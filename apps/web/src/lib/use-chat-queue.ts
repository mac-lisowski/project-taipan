"use client";

import { useSyncExternalStore } from "react";

import { useChatQueueStore } from "@/lib/chat-queue-context";
import type { ChatQueueSnapshot } from "@/lib/chat-queue";

// Queue snapshot for React consumers: the store comes from context, so
// each chat surface reads its own instance.
export function useChatQueue(): ChatQueueSnapshot {
  const store = useChatQueueStore();
  return useSyncExternalStore(
    store.subscribe,
    store.getSnapshot,
    store.getServerSnapshot,
  );
}
