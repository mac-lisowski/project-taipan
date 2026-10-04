import { type NextRequest, NextResponse } from "next/server";
import { copyHeaders, proxyUpstream } from "@/lib/upstream-proxy";

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

function publicOrigin(req: NextRequest): string {
  return PUBLIC_ORIGIN ?? `http://${req.headers.get("host") ?? "localhost"}`;
}

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

// Request-side policy lives in the upstream-proxy module; the
// response-side rewrite stays here until ticket 02 moves it.
async function proxy(req: NextRequest) {
  const upstream = await proxyUpstream(req, {
    upstreamUrl: apiInternalUrl(),
    publicOrigin: publicOrigin(req),
  });
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
