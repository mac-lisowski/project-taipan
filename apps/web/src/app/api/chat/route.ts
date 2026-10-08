import { type NextRequest } from "next/server";
import { proxyUpstream } from "@/lib/upstream-proxy";
import { apiInternalUrl, publicOrigin } from "../env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// A model turn can stream for minutes; the 30s default would cut it off.
const COMPLETION_TIMEOUT_MS = 300_000;

async function relay(req: NextRequest): Promise<Response> {
  // The browser path is /api/chat; the upstream route is /api/chat/complete.
  const url = new URL(req.url);
  url.pathname = "/api/chat/complete";
  const rewritten = new Request(url, {
    method: req.method,
    headers: req.headers,
    body: req.body,
    signal: req.signal,
    // Required by undici when the body is a stream.
    ...{ duplex: "half" },
  } as RequestInit);
  return proxyUpstream(rewritten, {
    upstreamUrl: apiInternalUrl(),
    publicOrigin: publicOrigin(),
    timeoutMs: COMPLETION_TIMEOUT_MS,
  });
}

export { relay as POST };
