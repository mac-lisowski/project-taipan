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

const PUBLIC_ORIGIN = process.env.PUBLIC_ORIGIN;

// The route is only an adapter: env resolution, the module call, and
// returning the final browser-facing Response.
async function proxy(req: NextRequest): Promise<Response> {
  return proxyUpstream(req, {
    upstreamUrl: apiInternalUrl(),
    publicOrigin:
      PUBLIC_ORIGIN ?? `http://${req.headers.get("host") ?? "localhost"}`,
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
