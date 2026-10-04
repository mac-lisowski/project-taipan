import { type NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://localhost:8000";

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
    new Set(["content-length", "accept-encoding"]),
  );
  for (const name of (req.headers.get("connection") ?? "").split(",")) {
    const n = name.trim();
    if (n) headers.delete(n);
  }
  headers.set("x-forwarded-host", req.headers.get("host") ?? "");
  const ip = req.headers.get("x-real-ip") ?? "127.0.0.1";
  const chain = req.headers.get("x-forwarded-for");
  headers.set("x-forwarded-for", chain ? `${chain}, ${ip}` : ip);
  return headers;
}

function rewriteLocation(location: string, publicOrigin: string): string {
  try {
    const upstream = new URL(location, API_INTERNAL_URL);
    if (upstream.origin !== new URL(API_INTERNAL_URL).origin) return location;
    return publicOrigin + upstream.pathname + upstream.search + upstream.hash;
  } catch {
    return location;
  }
}

// Host-bind the cookie: an upstream Domain attribute would be wrong on
// the public origin.
function hostBind(cookie: string): string {
  return cookie.replace(/;\s*domain=[^;]*/i, "");
}

async function proxy(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  const url = `${API_INTERNAL_URL}/api/${path.join("/")}${req.nextUrl.search}`;

  const upstream = await fetch(url, {
    method: req.method,
    headers: requestHeaders(req),
    body:
      req.method === "GET" || req.method === "HEAD"
        ? undefined
        : await req.arrayBuffer(),
    redirect: "manual",
  });

  const res = new NextResponse(upstream.body, { status: upstream.status });
  // content-encoding/length are stale after undici decompresses;
  // set-cookie and location get rewritten below.
  copyHeaders(
    upstream.headers,
    res.headers,
    new Set(["content-length", "content-encoding", "set-cookie", "location"]),
  );
  const location = upstream.headers.get("location");
  if (location) {
    res.headers.set("location", rewriteLocation(location, req.nextUrl.origin));
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
