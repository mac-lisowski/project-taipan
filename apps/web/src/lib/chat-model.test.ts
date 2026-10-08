import { afterEach, describe, expect, it, vi } from "vitest";

const MODELS = [
  { id: "fast", name: "Fast", default: true },
  { id: "smart", name: "Smart" },
];

function stubStorage(initial: Record<string, string> = {}, failing = false) {
  const store = new Map(Object.entries(initial));
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string): string | null => {
        if (failing) throw new Error("blocked");
        return store.get(key) ?? null;
      },
      setItem: (key: string, value: string): void => {
        if (failing) throw new Error("blocked");
        store.set(key, value);
      },
    },
    addEventListener: (): void => {},
    removeEventListener: (): void => {},
  });
  return store;
}

function stubModelsFetch(handler: () => { body: unknown; status?: number }) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", (url: unknown) => {
    calls.push(String(url));
    const { body, status = 200 } = handler();
    return Promise.resolve(new Response(JSON.stringify(body), { status }));
  });
  return calls;
}

async function freshState() {
  vi.resetModules();
  return import("./chat-model");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("model list load", () => {
  it("fetches the BFF models route once and resolves the API default", async () => {
    stubStorage();
    const calls = stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();

    await state.loadChatModels();
    await state.loadChatModels();

    expect(calls).toEqual(["/api/chat/models"]);
    const snap = state.readChatModelState();
    expect(snap.status).toBe("ready");
    expect(snap.models).toEqual(MODELS);
    expect(snap.currentId).toBe("fast");
  });

  it("restores a stored pick that is still in the list", async () => {
    stubStorage({ "taipan-chat-model": "smart" });
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();

    await state.loadChatModels();

    expect(state.readChatModelState().currentId).toBe("smart");
  });

  it("falls back to the API default when the stored id is not listed", async () => {
    stubStorage({ "taipan-chat-model": "gone" });
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();

    await state.loadChatModels();

    expect(state.readChatModelState().currentId).toBe("fast");
  });

  it("exposes an error state when the listing fails", async () => {
    stubStorage();
    stubModelsFetch(() => ({ body: { detail: "down" }, status: 500 }));
    const state = await freshState();

    await state.loadChatModels();

    const snap = state.readChatModelState();
    expect(snap.status).toBe("error");
    expect(snap.models).toEqual([]);
    expect(snap.currentId).toBeNull();
  });

  it("keeps no selection when the list is empty", async () => {
    stubStorage({ "taipan-chat-model": "smart" });
    stubModelsFetch(() => ({ body: [] }));
    const state = await freshState();

    await state.loadChatModels();

    const snap = state.readChatModelState();
    expect(snap.status).toBe("ready");
    expect(snap.currentId).toBeNull();
  });
});

describe("model selection", () => {
  it("persists the pick under the taipan key and notifies subscribers", async () => {
    const store = stubStorage();
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();
    const listener = vi.fn();
    const stop = state.chatModelStore.subscribe(listener);
    await state.loadChatModels();
    listener.mockClear();

    state.selectChatModel("smart");

    expect(store.get(state.CHAT_MODEL_STORAGE_KEY)).toBe("smart");
    expect(state.readChatModelState().currentId).toBe("smart");
    expect(listener).toHaveBeenCalledTimes(1);
    stop();
  });

  it("round-trips the pick across a reload", async () => {
    const store = stubStorage();
    stubModelsFetch(() => ({ body: MODELS }));
    const first = await freshState();
    await first.loadChatModels();

    first.selectChatModel("smart");

    const reloaded = await freshState();
    await reloaded.loadChatModels();
    expect(reloaded.readChatModelState().currentId).toBe("smart");
    expect(store.get("taipan-chat-model")).toBe("smart");
  });

  it("keeps the in-session pick when storage is blocked", async () => {
    stubStorage({}, true);
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();
    await state.loadChatModels();
    expect(state.readChatModelState().currentId).toBe("fast");

    expect(() => state.selectChatModel("smart")).not.toThrow();
    expect(state.readChatModelState().currentId).toBe("smart");
  });
});
