// Owns the request side of the BFF proxy: URL building, path
// re-encoding, header hygiene, timeout, and the upstream fetch call.
// Env resolution stays in the route handler and arrives as config, so
// tests can drive this seam with a plain Request and a stub fetch.

export type ProxyConfig = {
  // Base URL of the upstream API, resolved by the route handler.
  upstreamUrl: string;
  // Browser-facing origin for the forwarding headers rebuilt below.
  // Falls back to http plus the request Host.
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

// Shared with the route handler, which still applies the response-side
// header copy until ticket 02 moves that policy in here too.
export function copyHeaders(
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
    return await doFetch(`${cfg.upstreamUrl}/api/${encoded}${url.search}`, {
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
    } as RequestInit);
  } catch {
    return Response.json({ detail: "upstream unavailable" }, { status: 502 });
  }
}
