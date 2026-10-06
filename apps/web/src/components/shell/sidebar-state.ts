// Persisted sidebar open-state behind useSyncExternalStore: no setState
// in an effect, and the stored value applies without a render flash.
const STORAGE_KEY = "taipan-sidebar-open";

const listeners = new Set<() => void>();
let cached: boolean | null = null;

function loadStored(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== "0";
  } catch {
    return true;
  }
}

export function readSidebarOpen(): boolean {
  if (cached !== null) return cached;
  cached = loadStored();
  return cached;
}

// Cross-tab sync: a write in another tab re-reads storage and fans
// out here, so two tabs never diverge.
function subscribe(notify: () => void): () => void {
  listeners.add(notify);
  function onStorage(event: StorageEvent): void {
    if (event.key !== null && event.key !== STORAGE_KEY) return;
    cached = loadStored();
    notify();
  }
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(notify);
    window.removeEventListener("storage", onStorage);
  };
}

export function writeSidebarOpen(next: boolean): void {
  cached = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
  } catch {
    // Storage blocked: state still holds for this session.
  }
  listeners.forEach((notify) => notify());
}

export const sidebarOpenStore = {
  subscribe,
  getSnapshot: readSidebarOpen,
  getServerSnapshot: (): boolean => true,
};
