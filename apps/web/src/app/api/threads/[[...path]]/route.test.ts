import { afterEach, describe, expect, it, vi } from "vitest";

import * as route from "./route";

const UPSTREAM = "http://api:8000";

// The handlers only use the standard Request API, so the test seam drops
// the Next-specific wrapper.
type Handler = (req: Request) => Promise<Response>;
const handlers = route as unknown as Record<
  "GET" | "POST" | "PATCH" | "DELETE",
  Handler
>;

// The contract calls the storage adapter makes, plus the four queue calls.
const CASES = [
  { method: "GET", path: "/api/threads/get?cursor=cur-1" },
  { method: "POST", path: "/api/threads/create", body: '{"messages":[]}' },
  { method: "GET", path: "/api/threads/get/t-1" },
  {
    method: "PATCH",
    path: "/api/threads/update/t-1",
    body: '{"id":"t-1","title":"x","createdAt":1}',
  },
  { method: "DELETE", path: "/api/threads/delete/t-1" },
  // The queued-message contract; the catch-all relays it 1:1.
  {
    method: "POST",
    path: "/api/threads/queue/create",
    body: '{"threadId":"t-1","content":{"text":"hi"}}',
  },
  { method: "GET", path: "/api/threads/queue/get?thread_id=t-1" },
  {
    method: "PATCH",
    path: "/api/threads/queue/update/q-1",
    body: '{"content":{"text":"edited"}}',
  },
  { method: "DELETE", path: "/api/threads/queue/delete/q-1" },
] as const;

describe("threads BFF route", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each(CASES)(
    "$method $path relays method, path, and cookie upstream",
    async (c) => {
      vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
      const calls: { url: string; init: RequestInit }[] = [];
      vi.stubGlobal(
        "fetch",
        ((url: string | URL | Request, init?: RequestInit) => {
          calls.push({ url: String(url), init: init ?? {} });
          return Promise.resolve(new Response(null, { status: 204 }));
        }) as typeof fetch,
      );
      const handler = handlers[c.method];
      expect(handler).toBeTypeOf("function");
      const req = new Request(`http://web.test${c.path}`, {
        method: c.method,
        body: "body" in c ? c.body : undefined,
        headers: { cookie: "session=tok" },
      });
      const res = await handler(req);
      expect(calls).toHaveLength(1);
      const [call] = calls;
      if (!call) throw new Error("upstream fetch was not called");
      expect(call.url).toBe(`${UPSTREAM}${c.path}`);
      expect(call.init.method).toBe(c.method);
      const headers = call.init.headers;
      if (!(headers instanceof Headers)) throw new Error("no Headers upstream");
      expect(headers.get("cookie")).toBe("session=tok");
      // The proxy forwards the request body stream verbatim.
      expect(call.init.body ?? null).toBe("body" in c ? req.body : null);
      expect(res.status).toBe(204);
    },
  );
});
