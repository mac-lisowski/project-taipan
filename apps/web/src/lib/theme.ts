// Theme mode store: dark is default, a stored choice wins, tabs stay in sync.
export type ThemeMode = "dark" | "light";

export const THEME_STORAGE_KEY = "taipan-theme-mode";
export const THEME_DARK_CLASS = "dark";

// Anything but "light" resolves to dark, so corrupt storage keeps a theme.
export function resolveMode(stored: string | null): ThemeMode {
  return stored === "light" ? "light" : "dark";
}

export function applyModeClass(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle(THEME_DARK_CLASS, mode === "dark");
}

function loadStored(): ThemeMode {
  try {
    return resolveMode(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "dark";
  }
}

const listeners = new Set<() => void>();
let cached: ThemeMode | null = null;

export function readThemeMode(): ThemeMode {
  if (cached === null) cached = loadStored();
  return cached;
}

export function writeThemeMode(mode: ThemeMode): void {
  cached = mode;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    // Storage blocked: the mode still holds for this session.
  }
  applyModeClass(mode);
  listeners.forEach((notify) => notify());
}

export function toggleThemeMode(): void {
  writeThemeMode(readThemeMode() === "dark" ? "light" : "dark");
}

// Cross-tab sync mirrors the sidebar store: a foreign write re-reads storage.
function subscribe(notify: () => void): () => void {
  listeners.add(notify);
  function onStorage(event: StorageEvent): void {
    if (event.key !== THEME_STORAGE_KEY) return;
    cached = loadStored();
    applyModeClass(cached);
    notify();
  }
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(notify);
    window.removeEventListener("storage", onStorage);
  };
}

export const themeModeStore = {
  subscribe,
  getSnapshot: readThemeMode,
  getServerSnapshot: (): ThemeMode => "dark",
};

// Pre-paint snippet for the root layout: plain ES5, new Function-callable.
export function prePaintThemeScript(): string {
  const key = JSON.stringify(THEME_STORAGE_KEY);
  const darkClass = JSON.stringify(THEME_DARK_CLASS);
  return `(function(){try{var m=localStorage.getItem(${key});document.documentElement.classList.toggle(${darkClass},m!=="light")}catch(e){}})()`;
}
