import { afterEach, describe, expect, it, vi } from "vitest";

import {
  recordingFetch,
  type RecordedCall,
} from "@/lib/upstream-proxy.testsupport";

// The SDK factories are mocked so the test can pin the exact wiring the
// config module hands to AgentInterface.
const mocks = vi.hoisted(() => {
  const ADAPTER = { stream: true };
  const FORMAT = { wire: true };
  const innerListThreads = vi.fn(async () => ({ threads: [], nextCursor: undefined }));
  return {
    ADAPTER,
    FORMAT,
    fetchLLM: vi.fn(() => ({ kind: "llm" })),
    innerListThreads,
    restStorage: vi.fn(() => ({ kind: "storage", thread: { listThreads: innerListThreads } })),
    openAIAdapter: vi.fn(() => ADAPTER),
  };
});

vi.mock("@openuidev/react-headless", () => ({
  fetchLLM: mocks.fetchLLM,
  restStorage: mocks.restStorage,
  openAIAdapter: mocks.openAIAdapter,
  openAIMessageFormat: mocks.FORMAT,
}));

import { chatLLM, chatStorage } from "./chat-config";

describe("chat client config", () => {
  afterEach(() => {
    mocks.fetchLLM.mockClear();
    mocks.restStorage.mockClear();
    mocks.openAIAdapter.mockClear();
    mocks.innerListThreads.mockClear();
  });

  it("wires the llm transport to the chat BFF route in OpenAI shape", () => {
    chatLLM();
    expect(mocks.fetchLLM).toHaveBeenCalledWith({
      url: "/api/chat",
      streamAdapter: mocks.ADAPTER,
      messageFormat: mocks.FORMAT,
      fetch: expect.any(Function),
    });
  });

  it("wires thread storage to the threads BFF route in OpenAI shape", () => {
    chatStorage();
    expect(mocks.restStorage).toHaveBeenCalledWith({
      baseUrl: "/api/threads",
      messageFormat: mocks.FORMAT,
    });
  });
});

// The server render hands over one thread page; the storage answers the
// SDK's first list call from it so the sidebar paints with data.
describe("chat storage seed wrapper", () => {
  afterEach(() => {
    mocks.innerListThreads.mockClear();
  });

  it("answers only the first cursorless call from the seed", async () => {
    const storage = chatStorage({
      threads: [{ id: "t1", title: "T", createdAt: 1 }],
      nextCursor: "c1",
    });

    await expect(storage.thread.listThreads()).resolves.toEqual({
      threads: [{ id: "t1", title: "T", createdAt: 1 }],
      nextCursor: "c1",
    });
    await storage.thread.listThreads();
    expect(mocks.innerListThreads).toHaveBeenCalledTimes(1);
  });

  it("passes cursor calls through without consuming the seed", async () => {
    const storage = chatStorage({ threads: [{ id: "t1", title: "T", createdAt: 1 }] });

    await storage.thread.listThreads("c9");
    expect(mocks.innerListThreads).toHaveBeenCalledWith("c9");

    await expect(storage.thread.listThreads()).resolves.toEqual({
      threads: [{ id: "t1", title: "T", createdAt: 1 }],
    });
    expect(mocks.innerListThreads).toHaveBeenCalledTimes(1);
  });

  it("falls straight through when no seed exists", async () => {
    const storage = chatStorage(null);

    await storage.thread.listThreads();
    expect(mocks.innerListThreads).toHaveBeenCalledTimes(1);
  });
});

// The fetch handed to fetchLLM merges the live model id into the JSON
// body, so switching models never rebuilds the ChatLLM.
describe("completion fetch wrapper", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubWindow(): void {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (): string | null => null,
        setItem: (): void => {},
      },
      addEventListener: (): void => {},
      removeEventListener: (): void => {},
    });
  }

  // Fresh modules per test: the model id store is a singleton that must
  // not leak a pick between cases.
  async function wiredFetch(): Promise<typeof fetch> {
    vi.resetModules();
    const { chatLLM } = await import("./chat-config");
    chatLLM();
    const call = mocks.fetchLLM.mock.calls.at(-1) as unknown as
      | [{ fetch?: typeof fetch }]
      | undefined;
    const fetchImpl = call?.[0]?.fetch;
    if (typeof fetchImpl !== "function") {
      throw new Error("fetchLLM was not given a fetch");
    }
    return fetchImpl;
  }

  function sentBody(calls: RecordedCall[], index: number): Record<string, unknown> {
    const body = calls[index]?.init.body;
    if (typeof body !== "string") {
      throw new Error("request body was not a string");
    }
    return JSON.parse(body) as Record<string, unknown>;
  }

  it("sends the current model id inside the request body", async () => {
    stubWindow();
    const wrapper = await wiredFetch();
    const { selectChatModel } = await import("./chat-model");
    const { fetchImpl, calls } = recordingFetch();
    vi.stubGlobal("fetch", fetchImpl);

    selectChatModel("smart");
    await wrapper("/api/chat", {
      method: "POST",
      body: JSON.stringify({ threadId: "t" }),
    });

    expect(sentBody(calls, 0)).toEqual({ threadId: "t", model: "smart" });
  });

  it("reads the live model id on each request", async () => {
    stubWindow();
    const wrapper = await wiredFetch();
    const { selectChatModel } = await import("./chat-model");
    const { fetchImpl, calls } = recordingFetch();
    vi.stubGlobal("fetch", fetchImpl);

    selectChatModel("fast");
    await wrapper("/api/chat", { body: JSON.stringify({ n: 1 }) });
    selectChatModel("smart");
    await wrapper("/api/chat", { body: JSON.stringify({ n: 2 }) });

    expect(sentBody(calls, 0)).toEqual({ n: 1, model: "fast" });
    expect(sentBody(calls, 1)).toEqual({ n: 2, model: "smart" });
  });

  it("leaves the body untouched until a model is resolved", async () => {
    stubWindow();
    const wrapper = await wiredFetch();
    const { fetchImpl, calls } = recordingFetch();
    vi.stubGlobal("fetch", fetchImpl);

    await wrapper("/api/chat", { body: JSON.stringify({ threadId: "t" }) });

    expect(sentBody(calls, 0)).toEqual({ threadId: "t" });
  });
});
