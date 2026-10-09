import { type NextRequest } from "next/server";
import { proxyUpstream } from "@/lib/upstream-proxy";
import { apiInternalUrl, publicOrigin } from "../../../env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Public share read is a 1:1 path relay. GET only: the token is the
// credential, so a cookie is optional and writes stay unwired.
async function relay(req: NextRequest): Promise<Response> {
  return proxyUpstream(req, {
    upstreamUrl: apiInternalUrl(),
    publicOrigin: publicOrigin(),
  });
}

export { relay as GET };
