import { afterEach, describe, expect, it, vi } from "vitest";

import * as route from "./route";

const UPSTREAM = "http://api:8000";

// The handler only uses the standard Request API, so the test seam drops
// the Next-specific wrapper.
type Handler = (req: Request) => Promise<Response>;
const handlers = route as unknown as Record<"GET", Handler>;

function stubFetch(): { url: string; init: RequestInit }[] {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    ((url: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(url), init: init ?? {} });
      return Promise.resolve(
        new Response('{"detail":"no such share"}', { status: 404 }),
      );
    }) as typeof fetch,
  );
  return calls;
}

describe("public share relay", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("GETs the token path upstream and propagates the status", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = stubFetch();
    const res = await handlers.GET(
      new Request("http://web.test/api/public/threads/tok-1"),
    );
    const [call] = calls;
    if (!call) throw new Error("upstream fetch was not called");
    expect(call.url).toBe(`${UPSTREAM}/api/public/threads/tok-1`);
    expect(call.init.method).toBe("GET");
    expect(res.status).toBe(404);
  });

  it("relays with no cookie header at all", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = stubFetch();
    await handlers.GET(new Request("http://web.test/api/public/threads/tok-2"));
    const [call] = calls;
    if (!call) throw new Error("upstream fetch was not called");
    const headers = call.init.headers;
    if (!(headers instanceof Headers)) throw new Error("no Headers upstream");
    expect(headers.get("cookie")).toBeNull();
  });

  it("forwards a session cookie when one is present", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const calls = stubFetch();
    await handlers.GET(
      new Request("http://web.test/api/public/threads/tok-3", {
        headers: { cookie: "session=tok" },
      }),
    );
    const [call] = calls;
    if (!call) throw new Error("upstream fetch was not called");
    const headers = call.init.headers;
    if (!(headers instanceof Headers)) throw new Error("no Headers upstream");
    expect(headers.get("cookie")).toBe("session=tok");
  });

  // Snapshot reads must never cache: a revoke closes the link on the
  // next render, same as the threads relay convention.
  it("pins force-dynamic", () => {
    expect(route.dynamic).toBe("force-dynamic");
  });

  // The token is the credential: writes and verb probes stay unwired.
  it("exports GET only", () => {
    for (const m of ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]) {
      expect(route).not.toHaveProperty(m);
    }
  });
});
