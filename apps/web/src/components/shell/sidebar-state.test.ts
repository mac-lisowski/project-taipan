import { afterEach, describe, expect, it, vi } from "vitest";

type StorageHandler = (event: { key: string | null }) => void;

function stubStorage(initial: Record<string, string> = {}, failing = false) {
  const store = new Map(Object.entries(initial));
  const handlers = new Set<StorageHandler>();
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
    addEventListener: (type: string, handler: StorageHandler): void => {
      if (type === "storage") handlers.add(handler);
    },
    removeEventListener: (type: string, handler: StorageHandler): void => {
      if (type === "storage") handlers.delete(handler);
    },
  });
  return {
    store,
    emitStorage: (key: string | null): void => {
      handlers.forEach((handler) => handler({ key }));
    },
    handlerCount: (): number => handlers.size,
  };
}

async function freshState() {
  vi.resetModules();
  return import("./sidebar-state");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("sidebar open-state store", () => {
  it("opens by default when nothing is stored", async () => {
    stubStorage();
    const state = await freshState();
    expect(state.readSidebarOpen()).toBe(true);
  });

  it("reads the stored closed state", async () => {
    stubStorage({ "taipan-sidebar-open": "0" });
    const state = await freshState();
    expect(state.readSidebarOpen()).toBe(false);
  });

  it("persists writes and notifies subscribers", async () => {
    const { store, handlerCount } = stubStorage();
    const state = await freshState();
    const listener = vi.fn();
    const stop = state.sidebarOpenStore.subscribe(listener);

    state.writeSidebarOpen(false);

    expect(store.get("taipan-sidebar-open")).toBe("0");
    expect(state.readSidebarOpen()).toBe(false);
    expect(listener).toHaveBeenCalledTimes(1);

    stop();
    state.writeSidebarOpen(true);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(handlerCount()).toBe(0);
  });

  it("syncs writes made in another tab", async () => {
    const { store, emitStorage } = stubStorage();
    const state = await freshState();
    expect(state.readSidebarOpen()).toBe(true);
    const listener = vi.fn();
    state.sidebarOpenStore.subscribe(listener);

    store.set("taipan-sidebar-open", "0");
    emitStorage("taipan-sidebar-open");

    expect(state.readSidebarOpen()).toBe(false);
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("ignores storage events for other keys", async () => {
    const { emitStorage } = stubStorage();
    const state = await freshState();
    const listener = vi.fn();
    state.sidebarOpenStore.subscribe(listener);

    emitStorage("some-other-key");

    expect(state.readSidebarOpen()).toBe(true);
    expect(listener).not.toHaveBeenCalled();
  });

  it("stays open in-session when storage is blocked", async () => {
    stubStorage({}, true);
    const state = await freshState();
    expect(state.readSidebarOpen()).toBe(true);
    expect(() => state.writeSidebarOpen(false)).not.toThrow();
    expect(state.readSidebarOpen()).toBe(false);
  });
});
