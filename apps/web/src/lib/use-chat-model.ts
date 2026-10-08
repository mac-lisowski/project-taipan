"use client";

import { useSyncExternalStore } from "react";
import { chatModelStore, type ChatModelState } from "./chat-model";

// Snapshot for React consumers: the switcher reads status, models and
// the current id from the same store the fetch wrapper consults.
export function useChatModelState(): ChatModelState {
  return useSyncExternalStore(
    chatModelStore.subscribe,
    chatModelStore.getSnapshot,
    chatModelStore.getServerSnapshot,
  );
}
