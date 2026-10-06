import { type NextRequest } from "next/server";
import { proxyUpstream } from "@/lib/upstream-proxy";

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

// Same contract as API_INTERNAL_URL: missing in production fails deploy,
// or forwarded-proto headers and rewritten redirects go wrong.
function publicOrigin(): string | undefined {
  const origin = process.env.PUBLIC_ORIGIN;
  if (!origin && process.env.NODE_ENV === "production") {
    throw new Error("PUBLIC_ORIGIN is required in production");
  }
  return origin;
}

// The route is only an adapter: env resolution, the module call, and
// returning the final browser-facing Response.
async function proxy(req: NextRequest): Promise<Response> {
  return proxyUpstream(req, {
    upstreamUrl: apiInternalUrl(),
    // The module owns the publicOrigin fallback policy; it is testable there.
    publicOrigin: publicOrigin(),
  });
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
