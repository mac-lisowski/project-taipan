// Map-backed localStorage stub for unit tests that run without jsdom.
// Not a test file itself; the vitest include only matches *.test.ts.
import { vi } from "vitest";

// failing simulates blocked storage. The no-op event listeners cover
// stores that subscribe to cross-tab "storage" events. Returns the
// backing map for assertions.
export function stubStorage(
  initial: Record<string, string> = {},
  failing = false,
): Map<string, string> {
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
