import { useSyncExternalStore } from "react";

import { chatQueue, type ChatQueueSnapshot } from "@/lib/chat-queue";

// The queue store is a module singleton: there is one composer per app.
export function useChatQueue(): ChatQueueSnapshot {
  return useSyncExternalStore(
    chatQueue.subscribe,
    chatQueue.getSnapshot,
    chatQueue.getServerSnapshot,
  );
}
