import { afterEach, describe, expect, it, vi } from "vitest";

import {
  UPSTREAM,
  type RecordedCall,
  recordingFetch,
  request,
  requireCall,
} from "@/lib/upstream-proxy.testsupport";

import * as route from "./route";

// The handlers only use the standard Request API, so the test seam drops
// the Next-specific wrapper.
type Handler = (req: Request) => Promise<Response>;
const handlers = route as unknown as { GET: Handler };

function requireHeaders(calls: RecordedCall[]): Headers {
  const headers = requireCall(calls).init.headers;
  if (!(headers instanceof Headers)) {
    throw new Error("upstream fetch was not called with Headers");
  }
  return headers;
}

// The route resolves fetch at call time, so the seam stubs the global
// and records the upstream call instead of injecting a config fetch.
function stubUpstream(response: Response): RecordedCall[] {
  const { fetchImpl, calls } = recordingFetch(() => response);
  vi.stubGlobal("fetch", fetchImpl);
  return calls;
}

// /api/chat matches app/api/chat/route.ts exactly and exports only POST;
// the subpath falls through to this catch-all, which is the relay under
// test here.
describe("catch-all BFF route: GET /api/chat/models", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards the session cookie upstream", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = stubUpstream(Response.json({ data: [] }));
    const res = await handlers.GET(
      request("/api/chat/models", { headers: { cookie: "session=tok" } }),
    );
    expect(res.status).toBe(200);
    const call = requireCall(calls);
    expect(call.url).toBe(`${UPSTREAM}/api/chat/models`);
    expect(call.init.method).toBe("GET");
    expect(requireHeaders(calls).get("cookie")).toBe("session=tok");
  });

  // Byte identity of the stream object: the browser reader pulls straight
  // from the upstream body, so nothing can buffer or transform in between.
  it("relays the model list body byte-identical", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const payload =
      '[{"id":"fast","name":"Fast","default":true},{"id":"smart","name":"Smart"}]';
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(payload));
        controller.close();
      },
    });
    stubUpstream(
      new Response(body, {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const res = await handlers.GET(request("/api/chat/models"));
    expect(res.headers.get("content-type")).toBe("application/json");
    expect(res.body).toBe(body);
    await expect(res.text()).resolves.toBe(payload);
  });

  it("passes a non-200 upstream status and body through verbatim", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    stubUpstream(
      Response.json({ detail: "unauthenticated" }, { status: 401 }),
    );
    const res = await handlers.GET(
      request("/api/chat/models", { headers: { cookie: "session=bad" } }),
    );
    expect(res.status).toBe(401);
    await expect(res.json()).resolves.toEqual({ detail: "unauthenticated" });
  });

  // The LiteLLM gateway key lives only in the API; the BFF must never add one.
  it("injects no gateway material upstream", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = stubUpstream(Response.json({ data: [] }));
    await handlers.GET(
      request("/api/chat/models", { headers: { cookie: "session=tok" } }),
    );
    const headers = requireHeaders(calls);
    // Positive control: the real header traffic still arrives.
    expect(headers.get("cookie")).toBe("session=tok");
    expect(headers.get("authorization")).toBeNull();
    expect(headers.get("x-api-key")).toBeNull();
    expect(headers.get("x-litellm-api-key")).toBeNull();
  });
});
