"use client";

import { createContext, useContext, type ReactNode } from "react";

import { chatModelStore, type ChatModelStore } from "@/lib/chat-model";

// The main surface's singleton is the default so an unwrapped tree keeps
// current behavior; a second chat surface mounts the provider with its
// own createChatModelStore() instance (no storage key, so the pane pick
// never persists into the shared slot).
const ChatModelContext = createContext<ChatModelStore>(chatModelStore);

// The caller builds the store and hands it in; the pane also passes the
// same instance to chatLLM() so its completions carry its own pick.
export function ChatModelProvider({
  store,
  children,
}: {
  store: ChatModelStore;
  children: ReactNode;
}): ReactNode {
  return (
    <ChatModelContext.Provider value={store}>
      {children}
    </ChatModelContext.Provider>
  );
}

// The model store for this chat surface: the switcher loads/selects on
// it and the completion fetch reads its current id.
export function useChatModelStore(): ChatModelStore {
  return useContext(ChatModelContext);
}
