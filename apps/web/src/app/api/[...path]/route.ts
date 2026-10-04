import { type NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Resolved lazily: process.env is populated at runtime, not during
// `next build` page-data collection which also evaluates this module.
function apiInternalUrl(): string {
  const url = process.env.API_INTERNAL_URL;
  if (!url) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("API_INTERNAL_URL is required in production");
    }
    return "http://localhost:8000";
  }
  return url;
}

// Browser-facing origin for rewriting upstream redirects. Falls back
// to http + Host; set it explicitly in production.
const PUBLIC_ORIGIN = process.env.PUBLIC_ORIGIN;
const UPSTREAM_TIMEOUT_MS = 30_000;

function publicOrigin(req: NextRequest): string {
  return PUBLIC_ORIGIN ?? `http://${req.headers.get("host") ?? "localhost"}`;
}

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

// Rewritten below or stale after undici decompresses; server/
// x-powered-by would leak the internal stack.
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

function copyHeaders(
  src: Headers,
  dst: Headers,
  extraDrop: ReadonlySet<string> = new Set(),
) {
  src.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key) && !extraDrop.has(key)) dst.set(key, value);
  });
}

function requestHeaders(req: NextRequest): Headers {
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
  // req.nextUrl.origin derives scheme+host from client-supplied
  // x-forwarded-proto/host headers, so the fallback only trusts Host
  // with a fixed http scheme; production must set PUBLIC_ORIGIN.
  const origin = publicOrigin(req);
  headers.set("x-forwarded-host", req.headers.get("host") ?? "");
  headers.set("x-forwarded-proto", new URL(origin).protocol.replace(":", ""));
  // No client IP is trusted here: a spoofable XFF is worse than none.
  // FastAPI must only trust XFF when it sits behind this proxy anyway.
  return headers;
}

function rewriteLocation(location: string, publicOrigin: string): string {
  try {
    const upstream = new URL(location, apiInternalUrl());
    if (upstream.origin !== new URL(apiInternalUrl()).origin) return location;
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

function badPath(): NextResponse {
  return NextResponse.json({ detail: "invalid path" }, { status: 400 });
}

async function proxy(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  if (path.some((s) => s === "." || s === ".." || s.includes("\\"))) {
    return badPath();
  }
  // Params arrive decoded; re-encode so %2F, %23, %3F in a segment
  // cannot reshape the upstream path.
  const encoded = path.map(encodeURIComponent).join("/");
  const url = `${apiInternalUrl()}/api/${encoded}${req.nextUrl.search}`;

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers: requestHeaders(req),
      body: hasBody ? req.body : undefined,
      redirect: "manual",
      signal: AbortSignal.any([
        req.signal,
        AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
      ]),
      // Required by undici when the body is a stream.
      ...{ duplex: "half" },
    } as RequestInit);
  } catch {
    return NextResponse.json(
      { detail: "upstream unavailable" },
      { status: 502 },
    );
  }

  const body = NO_BODY_STATUS.has(upstream.status) ? null : upstream.body;
  const res = new NextResponse(body, { status: upstream.status });
  copyHeaders(upstream.headers, res.headers, RESPONSE_REWRITE);
  for (const name of ["location", "content-location"] as const) {
    const value = upstream.headers.get(name);
    if (value)
      res.headers.set(name, rewriteLocation(value, publicOrigin(req)));
  }
  for (const cookie of upstream.headers.getSetCookie()) {
    res.headers.append("set-cookie", hostBind(cookie));
  }
  return res;
}

export {
  proxy as GET,
  proxy as HEAD,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
  proxy as OPTIONS,
};
