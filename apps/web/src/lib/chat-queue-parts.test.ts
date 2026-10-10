import { describe, expect, it, vi } from "vitest";

import { createChatQueueStore, type QueueRow } from "./chat-queue";
import type { MessagePart } from "./attachments";

const THREAD = "11111111-1111-1111-1111-111111111111";

const BINARY: MessagePart[] = [
  {
    type: "binary",
    mimeType: "image/png",
    id: "f1",
    filename: "a.png",
    url: "/api/files/f1/content",
  },
];

function row(id: string, seq: number, text: string, parts?: MessagePart[]): QueueRow {
  return {
    id,
    threadId: THREAD,
    seq,
    content: parts === undefined ? { text } : { text, parts },
    createdAt: seq,
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
  });
}

type Call = { method: string; url: string; body: string | null };

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

describe("chat-queue attachment parts", () => {
  it("enqueue serializes {text, parts} through the content extras", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "POST" ? json(row("q1", 1, "see this", BINARY)) : json([]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);

    await store.enqueue("see this", BINARY);

    const post = calls.find((c) => c.method === "POST");
    expect(JSON.parse(post?.body ?? "null")).toEqual({
      threadId: THREAD,
      content: { text: "see this", parts: BINARY },
    });
    expect(store.getSnapshot().rows[0]?.content.parts).toEqual(BINARY);
  });

  it("dispatchHead rebuilds the [text, ...binary] parts content on send", async () => {
    const { impl } = stubFetch(() => json([row("a", 1, "see this", BINARY)]));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: (string | MessagePart[])[] = [];

    store.dispatchHead({
      send: vi.fn((content: string | MessagePart[]) => {
        sent.push(content);
        return Promise.resolve();
      }),
    });

    expect(sent).toEqual([[{ type: "text", text: "see this" }, ...BINARY]]);
    // Attribution still keys on the plain text the user typed.
    expect(store.getSnapshot().dispatch?.text).toBe("see this");
  });

  it("a text-only row still dispatches its string content", async () => {
    const { impl } = stubFetch(() => json([row("a", 1, "plain")]));
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);
    const sent: (string | MessagePart[])[] = [];

    store.dispatchHead({
      send: vi.fn((content: string | MessagePart[]) => {
        sent.push(content);
        return Promise.resolve();
      }),
    });

    expect(sent).toEqual(["plain"]);
  });

  it("editing a queued row keeps its parts in the PATCH body", async () => {
    const { impl, calls } = stubFetch((call) =>
      call.method === "PATCH"
        ? json(row("a", 1, "edited", BINARY))
        : json([row("a", 1, "see this", BINARY)]),
    );
    const store = createChatQueueStore(impl);
    await store.hydrate(THREAD);

    await store.update("a", "edited");

    const patch = calls.find((c) => c.method === "PATCH");
    // The API replaces content wholesale; dropping parts would lose the files.
    expect(JSON.parse(patch?.body ?? "null")).toEqual({
      content: { text: "edited", parts: BINARY },
    });
  });
});
