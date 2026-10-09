import { describe, expect, it, vi } from "vitest";

import { createChatQueueStore, type QueueRow } from "./chat-queue";

const THREAD = "11111111-1111-1111-1111-111111111111";
const OTHER = "22222222-2222-2222-2222-222222222222";

function row(id: string, seq: number): QueueRow {
  return {
    id,
    threadId: THREAD,
    seq,
    content: { text: `msg-${id}` },
    createdAt: seq,
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
  });
}

// A second chat surface builds its own store; nothing may cross over.
describe("separate queue store instances", () => {
  it("an enqueue on one instance leaves the other empty", async () => {
    const bPosts: string[] = [];
    const fetchA = (async (_url: unknown, init?: RequestInit) =>
      Promise.resolve(
        json(init?.method === "POST" ? row("qa", 2) : [row("a", 1)]),
      )) as typeof fetch;
    const fetchB = (async (_url: unknown, init?: RequestInit) => {
      if (init?.method === "POST") bPosts.push("POST");
      return Promise.resolve(json([row("b", 1)]));
    }) as typeof fetch;
    const storeA = createChatQueueStore(fetchA);
    const storeB = createChatQueueStore(fetchB);
    const notifyB = vi.fn();
    storeB.subscribe(notifyB);
    await storeA.hydrate(THREAD);
    await storeB.hydrate(THREAD);
    notifyB.mockClear();

    await storeA.enqueue("queued-a");

    expect(storeA.getSnapshot().rows.map((r) => r.id)).toEqual(["a", "qa"]);
    expect(storeB.getSnapshot().rows.map((r) => r.id)).toEqual(["b"]);
    expect(notifyB).not.toHaveBeenCalled();
    expect(bPosts).toEqual([]);
  });

  it("hydrate resets only its own thread state", async () => {
    const fetchA = (async (url: unknown) =>
      Promise.resolve(
        json(String(url).includes(OTHER) ? [row("a2", 1)] : [row("a1", 1)]),
      )) as typeof fetch;
    const fetchB = (async () =>
      Promise.resolve(json([row("b1", 1)]))) as typeof fetch;
    const storeA = createChatQueueStore(fetchA);
    const storeB = createChatQueueStore(fetchB);
    await storeA.hydrate(THREAD);
    await storeB.hydrate(THREAD);

    await storeA.hydrate(OTHER);

    expect(storeA.getSnapshot().threadId).toBe(OTHER);
    expect(storeA.getSnapshot().rows.map((r) => r.id)).toEqual(["a2"]);
    expect(storeB.getSnapshot().threadId).toBe(THREAD);
    expect(storeB.getSnapshot().rows.map((r) => r.id)).toEqual(["b1"]);
  });
});
