import { type NextRequest } from "next/server";
import { proxyUpstream } from "@/lib/upstream-proxy";
import { apiInternalUrl, publicOrigin } from "../env";


export const runtime = "nodejs";
export const dynamic = "force-dynamic";

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
