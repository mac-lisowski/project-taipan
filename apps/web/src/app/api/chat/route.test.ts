import { afterEach, describe, expect, it, vi } from "vitest";

import * as route from "./route";

const UPSTREAM = "http://api:8000";

// The handler only uses the standard Request API, so the test seam drops
// the Next-specific wrapper.
const handlers = route as unknown as {
  POST: (req: Request) => Promise<Response>;
};

// A completion-shaped POST that already carries the session cookie.
function chatRequest(init?: RequestInit): Request {
  return new Request("http://web.test/api/chat", {
    method: "POST",
    body: JSON.stringify({ threadId: "t1", runId: "r1", messages: [] }),
    headers: { "content-type": "application/json", cookie: "session=tok" },
    ...init,
  });
}

// Records the upstream call; never touches the network.
function recordedFetch(response: Response): { url: string; init: RequestInit }[] {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    ((url: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(url), init: init ?? {} });
      return Promise.resolve(response);
    }) as typeof fetch,
  );
  return calls;
}

function requireCall(calls: { url: string; init: RequestInit }[]): {
  url: string;
  init: RequestInit;
} {
  const call = calls[0];
  if (!call) throw new Error("upstream fetch was not called");
  return call;
}

describe("chat BFF route", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("exposes no GET handler, so prefetch cannot start a completion", () => {
    expect(route).not.toHaveProperty("GET");
  });

  it("relays POST to the upstream completion endpoint with the cookie", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = recordedFetch(new Response("{}", { status: 200 }));
    const res = await handlers.POST(chatRequest());
    expect(res.status).toBe(200);
    expect(requireCall(calls).url).toBe(`${UPSTREAM}/api/chat/complete`);
    const headers = requireCall(calls).init.headers;
    if (!(headers instanceof Headers)) throw new Error("no Headers upstream");
    expect(headers.get("cookie")).toBe("session=tok");
    expect(requireCall(calls).init.method).toBe("POST");
  });

  it("passes the SSE bytes through unchanged", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const sse = 'data: {"delta":"hi"}\n\ndata: [DONE]\n\n';
    recordedFetch(
      new Response(sse, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );
    const res = await handlers.POST(chatRequest());
    expect(res.headers.get("content-type")).toBe("text/event-stream");
    await expect(res.text()).resolves.toBe(sse);
  });

  // Byte identity of the stream object: the browser reader pulls straight
  // from the upstream body, so nothing can buffer in between.
  it("hands the upstream body stream to the browser unwrapped", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const body = new ReadableStream<Uint8Array>();
    recordedFetch(
      new Response(body, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );
    const res = await handlers.POST(chatRequest());
    expect(res.body).toBe(body);
  });

  it("propagates a client abort into the upstream signal", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = recordedFetch(new Response("data: x\n\n"));
    const controller = new AbortController();
    const pending = handlers.POST(chatRequest({ signal: controller.signal }));
    const signal = requireCall(calls).init.signal;
    if (!(signal instanceof AbortSignal)) throw new Error("no upstream signal");
    controller.abort();
    expect(signal.aborted).toBe(true);
    await pending;
  });

  it("uses the extended 300s budget for the completion", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    recordedFetch(new Response("{}"));
    const spy = vi.spyOn(AbortSignal, "timeout");
    await handlers.POST(chatRequest());
    expect(spy).toHaveBeenCalledWith(300_000);
  });

  // The provider key lives only in the API; the BFF must never add one.
  it("injects no authorization material upstream", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = recordedFetch(new Response("{}", { status: 200 }));
    await handlers.POST(chatRequest());
    const headers = requireCall(calls).init.headers;
    if (!(headers instanceof Headers)) throw new Error("no Headers upstream");
    expect(headers.get("authorization")).toBeNull();
  });
});
