// Owns the BFF proxy policy: URL building, header hygiene, timeout, upstream fetch, response build. Env arrives as config so tests drive this seam.

export type ProxyConfig = {
  // Base URL of the upstream API, resolved by the route handler.
  upstreamUrl: string;
  // Browser-facing origin for the forwarding headers; falls back to http plus the request Host.
  publicOrigin?: string;
  // Upstream abort budget in ms. Default 30_000.
  timeoutMs?: number;
  // Injectable for tests; defaults to globalThis.fetch.
  fetchImpl?: typeof fetch;
};

const HOP_BY_HOP = new Set([
  "connection",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

// Client-supplied forwarding info is never trusted; the proxy re-sets
// what it needs from values it controls.
const UNTRUSTED = new Set([
  "forwarded",
  "via",
  "x-real-ip",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-port",
  "x-forwarded-proto",
  "x-forwarded-scheme",
  "x-forwarded-server",
  "x-forwarded-ssl",
]);

const DEFAULT_TIMEOUT_MS = 30_000;

// Rewritten below or stale after undici decompresses; server/
// x-powered-by would leak the internal stack. set-cookie is re-emitted
// host-bound below instead of copied verbatim.
const RESPONSE_REWRITE = new Set([
  "content-length",
  "content-encoding",
  "set-cookie",
  "location",
  "content-location",
  "server",
  "x-powered-by",
]);

const NO_BODY_STATUS = new Set([101, 204, 205, 304]);

// Same-origin redirects must land on the public origin, not the
// internal one. Foreign origins and unparseable values pass through.
const BASE_ORIGINS = new Map<string, string>();

function rewriteLocation(
  location: string,
  baseUrl: string,
  publicOrigin: string,
): string {
  try {
    // Resolve against baseUrl, not a memoized origin: relative locations need the base path.
    const upstream = new URL(location, baseUrl);
    let baseOrigin = BASE_ORIGINS.get(baseUrl);
    if (!baseOrigin) {
      baseOrigin = new URL(baseUrl).origin;
      BASE_ORIGINS.set(baseUrl, baseOrigin);
    }
    if (upstream.origin !== baseOrigin) return location;
    return publicOrigin + upstream.pathname + upstream.search + upstream.hash;
  } catch {
    return location;
  }
}

// Host-bind the cookie: an upstream Domain attribute would be wrong on
// the public origin.
function hostBind(cookie: string): string {
  return cookie.replace(/;\s*domain=[^;]*/gi, "");
}

function copyHeaders(
  src: Headers,
  dst: Headers,
  extraDrop: ReadonlySet<string> = new Set(),
) {
  src.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key) && !extraDrop.has(key)) dst.set(key, value);
  });
}

function badPath(): Response {
  return Response.json({ detail: "invalid path" }, { status: 400 });
}

// Only Host is trusted for the origin fallback: client-supplied
// x-forwarded-* headers are stripped below, so they cannot steer it.
// Production sets an explicit origin via config.
function originFor(req: Request, explicit: string | undefined): string {
  return explicit ?? `http://${req.headers.get("host") ?? "localhost"}`;
}

function requestHeaders(req: Request, origin: string): Headers {
  const headers = new Headers();
  // content-length/accept-encoding: fetch recomputes them and undici
  // transparently decompresses; forwarding either breaks the hop.
  copyHeaders(
    req.headers,
    headers,
    new Set(["content-length", "accept-encoding", ...UNTRUSTED]),
  );
  for (const name of (req.headers.get("connection") ?? "").split(",")) {
    const n = name.trim();
    if (n) headers.delete(n);
  }
  headers.set("x-forwarded-host", req.headers.get("host") ?? "");
  headers.set("x-forwarded-proto", new URL(origin).protocol.replace(":", ""));
  // No client IP is trusted here: a spoofable XFF is worse than none.
  // FastAPI must only trust XFF when it sits behind this proxy anyway.
  return headers;
}

export async function proxyUpstream(
  req: Request,
  cfg: ProxyConfig,
): Promise<Response> {
  const url = new URL(req.url);
  if (!url.pathname.startsWith("/api/")) return badPath();
  const decoded: string[] = [];
  for (const segment of url.pathname.slice("/api/".length).split("/")) {
    try {
      decoded.push(decodeURIComponent(segment));
    } catch {
      // Malformed escape: fail closed as an invalid path.
      return badPath();
    }
  }
  if (decoded.some((s) => s === "." || s === ".." || s.includes("\\"))) {
    return badPath();
  }
  // Segments are decoded above; re-encode so %2F, %23, %3F in a
  // segment cannot reshape the upstream path.
  const encoded = decoded.map(encodeURIComponent).join("/");
  const origin = originFor(req, cfg.publicOrigin);

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const doFetch = cfg.fetchImpl ?? globalThis.fetch;
  try {
    const upstream = await doFetch(
      `${cfg.upstreamUrl}/api/${encoded}${url.search}`,
      {
        method: req.method,
        headers: requestHeaders(req, origin),
        body: hasBody ? req.body : undefined,
        redirect: "manual",
        signal: AbortSignal.any([
          req.signal,
          AbortSignal.timeout(cfg.timeoutMs ?? DEFAULT_TIMEOUT_MS),
        ]),
        // Required by undici when the body is a stream.
        ...{ duplex: "half" },
      } as RequestInit,
    );
    return browserResponse(upstream, cfg.upstreamUrl, origin);
  } catch {
    return Response.json({ detail: "upstream unavailable" }, { status: 502 });
  }
}

// Build the final Response the browser sees: the request-side result
// gets the response-side policy applied in one place.
function browserResponse(
  upstream: Response,
  upstreamUrl: string,
  publicOrigin: string,
): Response {
  const body = NO_BODY_STATUS.has(upstream.status) ? null : upstream.body;
  const res = new Response(body, { status: upstream.status });
  copyHeaders(upstream.headers, res.headers, RESPONSE_REWRITE);
  for (const name of ["location", "content-location"] as const) {
    const value = upstream.headers.get(name);
    if (value)
      res.headers.set(
        name,
        rewriteLocation(value, upstreamUrl, publicOrigin),
      );
  }
  for (const cookie of upstream.headers.getSetCookie()) {
    res.headers.append("set-cookie", hostBind(cookie));
  }
  return res;
}
