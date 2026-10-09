"use client";

import { useThread, useThreadList } from "@openuidev/react-headless";
import { useEffect, useRef } from "react";

import { useChatQueueStore } from "@/lib/chat-queue-context";

// Non-slot <AgentInterface> child (slots.rest): stays mounted on Route
// views where the composer unmounts.
export function QueueDispatch(): null {
  const isRunning = useThread((s) => s.isRunning);
  const messages = useThread((s) => s.messages);
  const processMessage = useThread((s) => s.processMessage);
  const selectedThreadId = useThreadList((s) => s.selectedThreadId);
  const queue = useChatQueueStore();
  const prevRunning = useRef(isRunning);

  useEffect(() => {
    void queue.hydrate(selectedThreadId);
  }, [queue, selectedThreadId]);

  // The rising edge is only attributed to the queue when the run's last
  // user message carries the dispatched text.
  useEffect(() => {
    const wasRunning = prevRunning.current;
    prevRunning.current = isRunning;
    if (isRunning) {
      if (!wasRunning) {
        const lastUser = messages.findLast((m) => m.role === "user");
        queue.noteRunStarted(
          typeof lastUser?.content === "string" ? lastUser.content : null,
        );
      }
      return;
    }
    if (!wasRunning) return;
    queue.handleRunEnd({
      threadId: selectedThreadId,
      // processMessage never rejects and resolves at run end; .catch guards
      // the QueueSend contract, not the SDK.
      send: (text) => processMessage({ role: "user", content: text }).catch(() => {}),
    });
  }, [queue, isRunning, messages, selectedThreadId, processMessage]);

  return null;
}
