import { afterEach, describe, expect, it, vi } from "vitest";

import { stubStorage } from "@/lib/storage-stub.testsupport";

const MODELS = [
  { id: "fast", name: "Fast", default: true },
  { id: "smart", name: "Smart" },
];

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

    await state.chatModelStore.load();
    await state.chatModelStore.load();

    expect(calls).toEqual(["/api/chat/models"]);
    const snap = state.chatModelStore.getSnapshot();
    expect(snap.status).toBe("ready");
    expect(snap.models).toEqual(MODELS);
    expect(snap.currentId).toBe("fast");
  });

  it("restores a stored pick that is still in the list", async () => {
    stubStorage({ "taipan-chat-model": "smart" });
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();

    await state.chatModelStore.load();

    expect(state.chatModelStore.getSnapshot().currentId).toBe("smart");
  });

  it("falls back to the API default when the stored id is not listed", async () => {
    stubStorage({ "taipan-chat-model": "gone" });
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();

    await state.chatModelStore.load();

    expect(state.chatModelStore.getSnapshot().currentId).toBe("fast");
  });

  it("exposes an error state when the listing fails", async () => {
    stubStorage();
    stubModelsFetch(() => ({ body: { detail: "down" }, status: 500 }));
    const state = await freshState();

    await state.chatModelStore.load();

    const snap = state.chatModelStore.getSnapshot();
    expect(snap.status).toBe("error");
    expect(snap.models).toEqual([]);
    expect(snap.currentId).toBeNull();
  });

  it("keeps no selection when the list is empty", async () => {
    stubStorage({ "taipan-chat-model": "smart" });
    stubModelsFetch(() => ({ body: [] }));
    const state = await freshState();

    await state.chatModelStore.load();

    const snap = state.chatModelStore.getSnapshot();
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
    await state.chatModelStore.load();
    listener.mockClear();

    state.chatModelStore.select("smart");

    expect(store.get(state.CHAT_MODEL_STORAGE_KEY)).toBe("smart");
    expect(state.chatModelStore.getSnapshot().currentId).toBe("smart");
    expect(listener).toHaveBeenCalledTimes(1);
    stop();
  });

  it("round-trips the pick across a reload", async () => {
    const store = stubStorage();
    stubModelsFetch(() => ({ body: MODELS }));
    const first = await freshState();
    await first.chatModelStore.load();

    first.chatModelStore.select("smart");

    const reloaded = await freshState();
    await reloaded.chatModelStore.load();
    expect(reloaded.chatModelStore.getSnapshot().currentId).toBe("smart");
    expect(store.get("taipan-chat-model")).toBe("smart");
  });

  it("keeps the in-session pick when storage is blocked", async () => {
    stubStorage({}, true);
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();
    await state.chatModelStore.load();
    expect(state.chatModelStore.getSnapshot().currentId).toBe("fast");

    expect(() => state.chatModelStore.select("smart")).not.toThrow();
    expect(state.chatModelStore.getSnapshot().currentId).toBe("smart");
  });
});

// A second chat surface builds its own store; persistence and cross-tab
// sync stay on the keyed main instance.
describe("per-instance model stores", () => {
  it("two instances hold independent picks", async () => {
    const store = stubStorage();
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();
    const main = state.createChatModelStore({
      storageKey: state.CHAT_MODEL_STORAGE_KEY,
    });
    const pane = state.createChatModelStore();
    await main.load();
    await pane.load();

    main.select("smart");
    expect(main.getSnapshot().currentId).toBe("smart");
    expect(pane.getSnapshot().currentId).toBe("fast");
    expect(store.get("taipan-chat-model")).toBe("smart");

    pane.select("fast");
    expect(pane.getSnapshot().currentId).toBe("fast");
    expect(main.getSnapshot().currentId).toBe("smart");
  });

  it("an unkeyed instance never writes the shared storage key", async () => {
    const store = stubStorage();
    stubModelsFetch(() => ({ body: MODELS }));
    const state = await freshState();
    const pane = state.createChatModelStore();

    await pane.load();
    pane.select("smart");

    expect(pane.getSnapshot().currentId).toBe("smart");
    expect(store.has("taipan-chat-model")).toBe(false);
  });

  it("only a keyed instance subscribes to storage events", async () => {
    const addEventListener = vi.fn();
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (): string | null => null,
        setItem: (): void => {},
      },
      addEventListener,
      removeEventListener: (): void => {},
    });
    const state = await freshState();
    const main = state.createChatModelStore({
      storageKey: state.CHAT_MODEL_STORAGE_KEY,
    });
    const pane = state.createChatModelStore();

    const stopPane = pane.subscribe(() => {});
    const stopMain = main.subscribe(() => {});

    expect(addEventListener).toHaveBeenCalledTimes(1);
    expect(addEventListener).toHaveBeenCalledWith("storage", expect.any(Function));
    stopMain();
    stopPane();
  });
});
