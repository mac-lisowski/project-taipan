"use client";

import { useSyncExternalStore } from "react";
import { useChatModelStore } from "./chat-model-context";
import type { ChatModelState } from "./chat-model";

// Snapshot for React consumers: the switcher reads status, models and
// the current id from the store this chat surface's context provides.
export function useChatModelState(): ChatModelState {
  const store = useChatModelStore();
  return useSyncExternalStore(
    store.subscribe,
    store.getSnapshot,
    store.getServerSnapshot,
  );
}
