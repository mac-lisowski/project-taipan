"use client";

import { ModelSwitcher } from "@openuidev/react-ui";
import { useEffect, type ReactNode } from "react";
import { useChatModelStore } from "@/lib/chat-model-context";
import { useChatModelState } from "@/lib/use-chat-model";

// Hidden until the list lands: while loading, and after an empty or
// failed response, there is nothing valid to pick and chat still works.
export function ChatModelSwitcher(): ReactNode {
  const store = useChatModelStore();
  const { status, models, currentId } = useChatModelState();
  useEffect(() => {
    void store.load();
  }, [store]);
  if (status !== "ready" || currentId === null) return null;
  return (
    <ModelSwitcher
      models={models}
      value={currentId}
      onValueChange={store.select}
    />
  );
}
