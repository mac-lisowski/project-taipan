"use client";

import { createContext, useContext, type ReactNode } from "react";

import { chatQueue, type ChatQueueStore } from "@/lib/chat-queue";

// The main surface's singleton is the default so an unwrapped tree keeps
// current behavior; a second chat surface mounts the provider with its
// own createChatQueueStore() instance.
const ChatQueueContext = createContext<ChatQueueStore>(chatQueue);

// The caller builds the store (fetch impl, lifetime) and hands it in, so
// the same provider serves the main chat and a pane.
export function ChatQueueProvider({
  store,
  children,
}: {
  store: ChatQueueStore;
  children: ReactNode;
}): ReactNode {
  return (
    <ChatQueueContext.Provider value={store}>
      {children}
    </ChatQueueContext.Provider>
  );
}

// The queue store for this chat surface: composer actions and the
// dispatch loop both go through it.
export function useChatQueueStore(): ChatQueueStore {
  return useContext(ChatQueueContext);
}
