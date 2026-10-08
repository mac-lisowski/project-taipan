import { afterEach, describe, expect, it, vi } from "vitest";

import { readSharedThread } from "./read-share";

const UPSTREAM = "http://api:8000";

const SNAPSHOT = {
  title: "demo thread",
  messages: [
    { role: "user", content: "hi" },
    { role: "assistant", content: "hello" },
  ],
};

describe("readSharedThread", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("GETs the snapshot per render with no-store and encodes the token", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(SNAPSHOT), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    expect(await readSharedThread("tok/1")).toEqual({
      ok: true,
      data: SNAPSHOT,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `${UPSTREAM}/api/public/threads/tok%2F1`,
      { cache: "no-store" },
    );
  });

  it("maps an upstream 404 to not-found", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    );
    expect(await readSharedThread("dead")).toEqual({
      ok: false,
      kind: "not-found",
    });
  });

  it("maps an upstream 5xx to upstream-down, not not-found", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 502 })),
    );
    expect(await readSharedThread("tok")).toEqual({
      ok: false,
      kind: "upstream-down",
    });
  });

  it("maps a thrown fetch to upstream-down instead of rejecting", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await readSharedThread("tok")).toEqual({
      ok: false,
      kind: "upstream-down",
    });
  });

  it("maps a malformed 200 payload to upstream-down", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ title: 7 }), { status: 200 }),
        ),
    );
    expect(await readSharedThread("tok")).toEqual({
      ok: false,
      kind: "upstream-down",
    });
  });

  // The API stores OpenAI-shaped messages verbatim, so content can be a
  // parts array. The page renders a fallback; validation must accept.
  it("accepts a snapshot whose message content is a parts array", async () => {
    vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
    const snapshot = {
      title: "demo thread",
      messages: [
        { role: "user", content: "hi" },
        {
          role: "assistant",
          content: [{ type: "text", text: "hello" }],
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(snapshot), { status: 200 }),
        ),
    );
    expect(await readSharedThread("tok")).toEqual({
      ok: true,
      data: snapshot,
    });
  });

  it.each([
    ["an unexpected role", { role: "tool", content: "bad role" }],
    ["a missing content key", { role: "assistant" }],
    ["a non-object entry", "just a string"],
  ])(
    "rejects a snapshot whose message entry has %s",
    async (_label, entry) => {
      vi.stubEnv("API_INTERNAL_URL", UPSTREAM);
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          new Response(
            JSON.stringify({
              title: "demo thread",
              messages: [{ role: "user", content: "hi" }, entry],
            }),
            { status: 200 },
          ),
        ),
      );
      expect(await readSharedThread("tok")).toEqual({
        ok: false,
        kind: "upstream-down",
      });
    },
  );
});
