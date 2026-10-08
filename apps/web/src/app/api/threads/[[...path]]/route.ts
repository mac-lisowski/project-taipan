import { type NextRequest } from "next/server";
import { proxyUpstream } from "@/lib/upstream-proxy";
import { apiInternalUrl, publicOrigin } from "../../env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Threads CRUD is a 1:1 path relay; only the completion route needs a
// path rewrite or a longer budget.
async function relay(req: NextRequest): Promise<Response> {
  return proxyUpstream(req, {
    upstreamUrl: apiInternalUrl(),
    publicOrigin: publicOrigin(),
  });
}

export { relay as GET, relay as POST, relay as PATCH, relay as DELETE };
