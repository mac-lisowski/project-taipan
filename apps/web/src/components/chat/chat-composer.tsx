"use client";

import { useThread } from "@openuidev/react-headless";
import { IconButton, type ConversationStarterProps } from "@openuidev/react-ui";
import { ArrowUp, Lightbulb, Square } from "lucide-react";
import {
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { QueueChips } from "@/components/chat/queue-chips";
import { useChatQueueStore } from "@/lib/chat-queue-context";
import { useChatQueue } from "@/lib/use-chat-queue";

// Matches the SDK composer: Enter submits, Shift+Enter and IME composition do not.
const IME_KEY_CODE = 229;

type ChatComposerProps = {
  starters: ConversationStarterProps[];
  placeholder?: string;
};

// Mode C composer children get no props, so all thread state comes from hooks.
export function ChatComposer({
  starters,
  placeholder = "Type your query here",
}: ChatComposerProps): ReactNode {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const processMessage = useThread((s) => s.processMessage);
  const cancelMessage = useThread((s) => s.cancelMessage);
  const isRunning = useThread((s) => s.isRunning);
  const isLoadingMessages = useThread((s) => s.isLoadingMessages);
  const messages = useThread((s) => s.messages);
  const queue = useChatQueue();
  const queueStore = useChatQueueStore();

  function send(textValue: string): Promise<void> {
    return processMessage({ role: "user", content: textValue });
  }

  function submit(): void {
    const value = text.trim();
    if (!value || isLoadingMessages) return;
    if (isRunning) {
      // Keep the draft when the enqueue fails (e.g. the 422 depth cap).
      void queueStore.enqueue(value).then((ok) => {
        if (ok) setText("");
      });
      return;
    }
    void send(value);
    setText("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>): void {
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !e.nativeEvent.isComposing &&
      e.keyCode !== IME_KEY_CODE
    ) {
      e.preventDefault();
      submit();
    }
  }

  const showStarters = messages.length === 0 && !isLoadingMessages;

  return (
    <>
      {showStarters && starters.length > 0 ? (
        <div className="openui-agent-conversation-starter openui-agent-conversation-starter--short">
          {starters.map((starter) => (
            <button
              key={starter.displayText}
              type="button"
              className="openui-agent-conversation-starter-item-short"
              onClick={() => void send(starter.prompt)}
            >
              <span className="openui-agent-conversation-starter-item-short__icon">
                {starter.icon ?? <Lightbulb size={16} />}
              </span>
              <span className="openui-agent-conversation-starter-item-short__text">
                {starter.displayText}
              </span>
            </button>
          ))}
        </div>
      ) : null}
      <div
        className="openui-agent-thread-composer"
        data-drafting={text.length > 0 || undefined}
        onClick={(e) => {
          // Form fields inside the container (queue edit input) keep focus.
          if (
            e.target instanceof Element &&
            !e.target.closest("button, a, [role='button'], input, textarea")
          ) {
            inputRef.current?.focus();
          }
        }}
      >
        <QueueChips
          queue={queue}
          canSendHead={!isRunning && !isLoadingMessages}
          onEdit={(id, next) => void queueStore.update(id, next)}
          onRemove={(id) => void queueStore.remove(id)}
          onSendHead={() => queueStore.dispatchHead({ send })}
        />
        <div className="openui-agent-thread-composer__input-wrapper">
          <textarea
            ref={inputRef}
            value={text}
            autoFocus
            onChange={(e) => setText(e.target.value)}
            className="openui-agent-thread-composer__input"
            placeholder={placeholder}
            rows={1}
            onKeyDown={onKeyDown}
          />
          <div className="openui-agent-thread-composer__action-bar">
            <IconButton
              onClick={isRunning ? cancelMessage : submit}
              icon={
                isRunning ? (
                  <Square size="1em" fill="currentColor" />
                ) : (
                  <ArrowUp size="1em" />
                )
              }
              size="extra-small"
              variant="primary"
              aria-label={isRunning ? "Cancel message" : "Send message"}
              className="openui-agent-thread-composer__submit-button"
            />
          </div>
        </div>
      </div>
    </>
  );
}
