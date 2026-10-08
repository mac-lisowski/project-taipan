import { afterEach, describe, expect, it, vi } from "vitest";

type ClassToggler = (name: string, force: boolean) => void;

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

function stubDocument(): { toggles: ClassToggler[]; calls: Array<[string, boolean]> } {
  const calls: Array<[string, boolean]> = [];
  const toggles: ClassToggler[] = [];
  vi.stubGlobal("document", {
    documentElement: {
      classList: {
        get toggle(): ClassToggler {
          const toggle: ClassToggler = (name, force) => {
            calls.push([name, force]);
            return force;
          };
          toggles.push(toggle);
          return toggle;
        },
      },
    },
  });
  return { toggles, calls };
}

async function freshState() {
  vi.resetModules();
  return import("./theme");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("theme mode resolution", () => {
  it("prefers the stored light value", async () => {
    stubStorage({ "taipan-theme-mode": "light" });
    const state = await freshState();
    expect(state.readThemeMode()).toBe("light");
  });

  it("prefers the stored dark value", async () => {
    stubStorage({ "taipan-theme-mode": "dark" });
    const state = await freshState();
    expect(state.readThemeMode()).toBe("dark");
  });

  it("falls back to dark when nothing is stored", async () => {
    stubStorage();
    const state = await freshState();
    expect(state.readThemeMode()).toBe("dark");
  });

  it("falls back to dark on an unknown stored value", async () => {
    stubStorage({ "taipan-theme-mode": "sepia" });
    const state = await freshState();
    expect(state.readThemeMode()).toBe("dark");
  });

  it("falls back to dark when storage is blocked", async () => {
    stubStorage({}, true);
    const state = await freshState();
    expect(state.readThemeMode()).toBe("dark");
  });
});

describe("theme mode toggle", () => {
  it("flips the exposed mode and notifies subscribers", async () => {
    stubStorage();
    const state = await freshState();
    const listener = vi.fn();
    const stop = state.themeModeStore.subscribe(listener);

    expect(state.themeModeStore.getSnapshot()).toBe("dark");
    state.toggleThemeMode();
    expect(state.themeModeStore.getSnapshot()).toBe("light");
    expect(listener).toHaveBeenCalledTimes(1);

    state.toggleThemeMode();
    expect(state.themeModeStore.getSnapshot()).toBe("dark");

    stop();
    state.toggleThemeMode();
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("keeps the in-session mode when storage is blocked", async () => {
    stubStorage({}, true);
    const state = await freshState();
    expect(() => state.toggleThemeMode()).not.toThrow();
    expect(state.themeModeStore.getSnapshot()).toBe("light");
  });

  it("applies the root class on every write", async () => {
    stubStorage();
    const { calls } = stubDocument();
    const state = await freshState();

    state.toggleThemeMode();

    expect(calls).toEqual([["dark", false]]);
  });
});

describe("theme persistence", () => {
  it("round-trips the storage key", async () => {
    const store = stubStorage();
    const state = await freshState();

    state.writeThemeMode("light");
    expect(store.get("taipan-theme-mode")).toBe("light");

    const reloaded = await freshState();
    expect(reloaded.readThemeMode()).toBe("light");

    reloaded.writeThemeMode("dark");
    expect(store.get("taipan-theme-mode")).toBe("dark");
    const reloadedAgain = await freshState();
    expect(reloadedAgain.readThemeMode()).toBe("dark");
  });
});

describe("pre-paint script", () => {
  function runScript(
    script: string,
    getItem: (key: string) => string | null,
  ): { calls: Array<[string, boolean]>; reads: string[] } {
    const calls: Array<[string, boolean]> = [];
    const reads: string[] = [];
    const document = {
      documentElement: {
        classList: {
          toggle: (name: string, force: boolean): boolean => {
            calls.push([name, force]);
            return force;
          },
        },
      },
    };
    const localStorage = {
      getItem: (key: string): string | null => {
        reads.push(key);
        return getItem(key);
      },
    };
    new Function("document", "localStorage", script)(document, localStorage);
    return { calls, reads };
  }

  it("reads the exported storage key and keeps dark when empty", async () => {
    const state = await freshState();
    const { calls, reads } = runScript(state.prePaintThemeScript(), () => null);
    expect(reads).toEqual([state.THEME_STORAGE_KEY]);
    expect(calls).toEqual([["dark", true]]);
  });

  it("drops the dark class for a stored light value", async () => {
    const state = await freshState();
    const { calls } = runScript(state.prePaintThemeScript(), () => "light");
    expect(calls).toEqual([["dark", false]]);
  });

  it("does nothing when storage access throws", async () => {
    const state = await freshState();
    const document = {
      documentElement: { classList: { toggle: (): boolean => false } },
    };
    const localStorage = { getItem: (): string => { throw new Error("blocked"); } };
    expect(() =>
      new Function("document", "localStorage", state.prePaintThemeScript())(
        document,
        localStorage,
      ),
    ).not.toThrow();
  });
});
