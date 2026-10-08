import { afterEach, describe, expect, it, vi } from "vitest";
import {
  generateShareLink,
  getShareStatus,
  revokeShareLink,
} from "./share-link";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateShareLink", () => {
  it("posts to the create endpoint and returns an absolute share URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ token: "tok-1" }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const url = await generateShareLink("thread-9", "https://chat.example.com");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/shares/create/thread-9",
      { method: "POST" },
    );
    expect(url).toBe("https://chat.example.com/share/tok-1");
  });

  it("encodes the thread id in the create URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ token: "tok-5" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generateShareLink("thr/ead", "https://chat.example.com");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/shares/create/thr%2Fead",
      { method: "POST" },
    );
  });

  it("reads window.location.origin when no origin is passed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ token: "tok-3" }), { status: 200 }),
      ),
    );
    vi.stubGlobal("window", { location: { origin: "https://app.example" } });

    expect(await generateShareLink("t")).toBe("https://app.example/share/tok-3");
  });

  it("rejects on a non-OK response so the modal shows no bogus link", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 500 })),
    );

    await expect(
      generateShareLink("t", "https://chat.example.com"),
    ).rejects.toThrow("share create failed: request failed (500)");
  });

  it("keeps the upstream detail line in the thrown error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "thread not found" }), {
          status: 404,
        }),
      ),
    );

    await expect(
      generateShareLink("t", "https://chat.example.com"),
    ).rejects.toThrow("share create failed: thread not found");
  });

  it("rejects when the success body carries no token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ unexpected: true }), { status: 200 }),
      ),
    );

    await expect(
      generateShareLink("t", "https://chat.example.com"),
    ).rejects.toThrow("share create returned no token");
  });
});

describe("revokeShareLink", () => {
  it("DELETEs the share endpoint and reports ok", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await revokeShareLink("thread-9")).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/shares/delete/thread-9",
      { method: "DELETE" },
    );
  });

  it("encodes the thread id in the delete URL", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await revokeShareLink("thr/ead");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/shares/delete/thr%2Fead",
      { method: "DELETE" },
    );
  });

  it("reports false on a non-OK response so the caller keeps the button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("gone", { status: 404 })),
    );

    expect(await revokeShareLink("thread-9")).toBe(false);
  });
});

describe("getShareStatus", () => {
  it("GETs the status endpoint and reports a live share", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ shared: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await getShareStatus("thr/ead")).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/shares/get/thr%2Fead",
    );
  });

  it("reports false when the API says not shared", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ shared: false }), { status: 200 }),
      ),
    );

    expect(await getShareStatus("thread-9")).toBe(false);
  });

  it("reports false on a non-OK response so the button stays hidden", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    );

    expect(await getShareStatus("thread-9")).toBe(false);
  });

  it("reports false on a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));

    expect(await getShareStatus("thread-9")).toBe(false);
  });
});
