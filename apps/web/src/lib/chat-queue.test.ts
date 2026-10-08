import { describe, expect, it, vi } from "vitest";

import { createChatQueueStore, type QueueRow } from "./chat-queue";

const THREAD = "11111111-1111-1111-1111-111111111111";
const OTHER = "22222222-2222-2222-2222-222222222222";

function makeRow(id: string, seq: number, text = `msg-${id}`): QueueRow {
  return {
    id,
    threadId: THREAD,
    seq,
    content: { text },
    createdAt: 1700000000 + seq,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

type Call = { method: string; url: string; body: string | null };

// Records each request synchronously so assertions can run without waiting
// on the store's fire-and-forget writes.
function stubFetch(responder: (call: Call) => Response) {
  const calls: Call[] = [];
  const impl = (async (url: string | URL | Request, init?: RequestInit) => {
    const call: Call = {
      method: init?.method ?? "GET",
      url: String(url),
      body: typeof init?.body === "string" ? init.body : null,
    };
    calls.push(call);
    return responder(call);
  }) as typeof fetch;
  return { impl, calls };
}

function makeSend(sent: string[]) {
  return vi.fn((text: string) => {
    sent.push(text);
    return Promise.resolve();
  });
}

describe("chat-queue store", () => {
  it("hydrate loads rows ordered by seq and binds the thread", async () => {
    const { impl, calls } = stubFetch(() =>
      json([makeRow("b", 2), makeRow("a", 1)]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    expect(store.getSnapshot().threadId).toBe(THREAD);
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["a", "b"]);
    expect(calls).toEqual([
      {
        method: "GET",
        url: `/api/threads/queue/get?thread_id=${THREAD}`,
        body: null,
      },
    ]);
  });

  it("switching threads swaps the queue", async () => {
    const { impl } = stubFetch((call) =>
      json(call.url.includes(THREAD) ? [makeRow("a", 1)] : [makeRow("c", 1)]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["a"]);
    await store.hydrate(OTHER);
    expect(store.getSnapshot().threadId).toBe(OTHER);
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["c"]);
  });

  it("hydrate failure surfaces a notice", async () => {
    const { impl } = stubFetch(() => new Response(null, { status: 500 }));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    expect(store.getSnapshot().notice).toBe("sync-failed");
    expect(store.getSnapshot().rows).toEqual([]);
  });

  it("enqueue posts the row and appends it to state", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "POST" ? json(makeRow("q1", 1, "hello")) : json([]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    await store.enqueue("hello");
    const post = calls.find((c) => c.method === "POST");
    expect(post?.url).toBe("/api/threads/queue/create");
    expect(JSON.parse(post?.body ?? "null")).toEqual({
      threadId: THREAD,
      content: { text: "hello" },
    });
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["q1"]);
    expect(store.getSnapshot().notice).toBeNull();
  });

  it("enqueue with no active thread is a no-op", async () => {
    const { impl, calls } = stubFetch(() => json(makeRow("q1", 1)));
    const store = createChatQueueStore(impl);
    await store.enqueue("hello");
    expect(calls).toEqual([]);
    expect(store.getSnapshot().rows).toEqual([]);
  });

  it("enqueue failure (e.g. the 422 depth cap) surfaces a notice", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "POST" ? new Response(null, { status: 422 }) : json([]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    await store.enqueue("hello");
    expect(store.getSnapshot().notice).toBe("enqueue-failed");
    expect(store.getSnapshot().rows).toEqual([]);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
  });

  it("update patches the row and replaces it in state", async () => {
    const rows = [makeRow("a", 1)];
    const { impl, calls } = stubFetch((call) =>
      call.method === "PATCH"
        ? json(makeRow("a", 1, "edited"))
        : json(rows),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    await store.update("a", "edited");
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.url).toBe("/api/threads/queue/update/a");
    expect(JSON.parse(patch?.body ?? "null")).toEqual({
      content: { text: "edited" },
    });
    expect(store.getSnapshot().rows[0]?.content.text).toBe("edited");
  });

  it("remove deletes the row and drops it from state", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "DELETE"
        ? new Response(null, { status: 204 })
        : json([makeRow("a", 1)]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    await store.remove("a");
    const del = calls.find((c) => c.method === "DELETE");
    expect(del?.url).toBe("/api/threads/queue/delete/a");
    expect(store.getSnapshot().rows).toEqual([]);
  });

  it("falling-edge dispatch sends the head and deletes the row once the run starts", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "DELETE"
        ? new Response(null, { status: 204 })
        : json([makeRow("a", 1, "first"), makeRow("b", 2, "second")]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: string[] = [];
    const send = makeSend(sent);

    store.handleRunEnd({ send, threadId: THREAD });
    expect(sent).toEqual(["first"]);
    expect(store.getSnapshot().dispatch?.id).toBe("a");

    // isRunning flipped true carrying the dispatched text: the run was
    // accepted, so the row is deleted and the chip drops.
    store.noteRunStarted("first");
    expect(
      calls.some(
        (c) => c.method === "DELETE" && c.url === "/api/threads/queue/delete/a",
      ),
    ).toBe(true);
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["b"]);

    // Run ends: the next head dispatches off the same edge.
    store.handleRunEnd({ send, threadId: THREAD });
    expect(sent).toEqual(["first", "second"]);
    expect(store.getSnapshot().dispatch?.id).toBe("b");
  });

  it("a rising edge with different text does not mark the dispatch started", async () => {
    const { impl, calls } = stubFetch(() => json([makeRow("a", 1, "first")]));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: string[] = [];
    const send = makeSend(sent);

    store.dispatchHead({ send });
    store.noteRunStarted("someone else's message");

    // An unrelated run must not consume the row.
    expect(store.getSnapshot().dispatch?.started).toBe(false);
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["a"]);
  });

  it("a started run that errors does not resend the consumed row", async () => {
    const { impl } = stubFetch(() => json([makeRow("a", 1, "first"), makeRow("b", 2, "second")]));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: string[] = [];
    const send = makeSend(sent);

    store.dispatchHead({ send });
    store.noteRunStarted("first");
    // The run errored after start: the row is already in history, so the
    // loop moves to the next head instead of duplicating "first".
    store.handleRunEnd({ send, threadId: THREAD });

    expect(sent).toEqual(["first", "second"]);
    expect(store.getSnapshot().dispatch?.id).toBe("b");
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["b"]);
  });

  it("a send that never starts retries once, then fails; manual send clears it", async () => {
    const { impl, calls } = stubFetch(() => json([makeRow("a", 1, "first")]));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: string[] = [];
    const send = makeSend(sent);

    store.dispatchHead({ send });
    expect(sent).toEqual(["first"]);

    // The busy run's edge arrives while the send never started: retry.
    store.handleRunEnd({ send, threadId: THREAD });
    expect(sent).toEqual(["first", "first"]);
    expect(store.getSnapshot().dispatch?.attempts).toBe(2);

    // Second never-started edge: give up and flag the row for manual send.
    store.handleRunEnd({ send, threadId: THREAD });
    expect(store.getSnapshot().dispatch).toBeNull();
    expect(store.getSnapshot().failedId).toBe("a");
    expect(store.getSnapshot().rows.map((r) => r.id)).toEqual(["a"]);
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);

    // Manual send clears the failed flag and re-dispatches the head.
    store.dispatchHead({ send });
    expect(store.getSnapshot().failedId).toBeNull();
    expect(sent).toEqual(["first", "first", "first"]);
    store.noteRunStarted("first");
    store.handleRunEnd({ send, threadId: THREAD });
    expect(store.getSnapshot().rows).toEqual([]);
  });

  it("run end on another thread or with no queue is ignored", () => {
    const { impl } = stubFetch(() => json([makeRow("a", 1)]));
    const store = createChatQueueStore(impl);
    return store.hydrate(THREAD).then(() => {
      const send = makeSend([]);
      store.handleRunEnd({ send, threadId: OTHER });
      expect(send).not.toHaveBeenCalled();
      store.handleRunEnd({ send, threadId: null });
      expect(send).not.toHaveBeenCalled();
    });
  });
});
