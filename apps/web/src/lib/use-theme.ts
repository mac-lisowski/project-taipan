"use client";

import { useSyncExternalStore } from "react";
import { themeModeStore, type ThemeMode } from "./theme";

// Active mode for React consumers: the chat theme provider and shell
// controls read the same store the pre-paint script seeds.
export function useThemeMode(): ThemeMode {
  return useSyncExternalStore(
    themeModeStore.subscribe,
    themeModeStore.getSnapshot,
    themeModeStore.getServerSnapshot,
  );
}
