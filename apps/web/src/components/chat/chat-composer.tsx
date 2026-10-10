"use client";

import { useThread } from "@openuidev/react-headless";
import { IconButton, type ConversationStarterProps } from "@openuidev/react-ui";
import { ArrowUp, Lightbulb, Paperclip, Square } from "lucide-react";
import {
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { AttachmentChips } from "@/components/chat/attachment-chips";
import { QueueChips } from "@/components/chat/queue-chips";
import {
  ATTACH_ACCEPT,
  MAX_ATTACHMENTS,
  acceptFor,
  binaryPart,
  removeAttachment,
  uploadAttachment,
  type AttachmentDraft,
  type BinaryPart,
  type MessagePart,
} from "@/lib/attachments";
import { useChatQueueStore } from "@/lib/chat-queue-context";
import { useChatModelState } from "@/lib/use-chat-model";
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
  const [drafts, setDrafts] = useState<AttachmentDraft[]>([]);
  const [hint, setHint] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const keySeq = useRef(0);
  // Chips removed mid-upload delete their file row once it exists.
  const cancelled = useRef(new Set<string>());
  const processMessage = useThread((s) => s.processMessage);
  const cancelMessage = useThread((s) => s.cancelMessage);
  const isRunning = useThread((s) => s.isRunning);
  const isLoadingMessages = useThread((s) => s.isLoadingMessages);
  const messages = useThread((s) => s.messages);
  const queue = useChatQueue();
  const queueStore = useChatQueueStore();
  const modelState = useChatModelState();
  const model = modelState.models.find((m) => m.id === modelState.currentId);
  const vision = model?.vision === true;

  function send(content: string | MessagePart[]): Promise<void> {
    return processMessage({ role: "user", content });
  }

  function onPick(e: ChangeEvent<HTMLInputElement>): void {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    setHint(null);
    let room = MAX_ATTACHMENTS - drafts.length;
    for (const file of files) {
      if (room <= 0) {
        setHint(`Up to ${MAX_ATTACHMENTS} attachments per message.`);
        break;
      }
      if (!acceptFor(file.type, vision)) {
        setHint(
          file.type.startsWith("image/")
            ? "The selected model has no vision support; images are off."
            : `${file.name}: unsupported file type.`,
        );
        continue;
      }
      room -= 1;
      const key = `a${++keySeq.current}`;
      const draft: AttachmentDraft = {
        key,
        status: "uploading",
        id: null,
        mimeType: file.type,
        filename: file.name,
        url: null,
      };
      setDrafts((prev) => [...prev, draft]);
      uploadAttachment(file)
        .then((ref) => {
          if (cancelled.current.has(key)) {
            cancelled.current.delete(key);
            void removeAttachment(ref.id);
            return;
          }
          setDrafts((prev) =>
            prev.map((d) =>
              d.key === key ? { ...d, ...ref, status: "ready" } : d,
            ),
          );
        })
        .catch(() => {
          setDrafts((prev) =>
            prev.map((d) => (d.key === key ? { ...d, status: "failed" } : d)),
          );
        });
    }
  }

  function onRemove(key: string): void {
    const draft = drafts.find((d) => d.key === key);
    setDrafts((prev) => prev.filter((d) => d.key !== key));
    if (draft === undefined) return;
    if (draft.id !== null) void removeAttachment(draft.id);
    else cancelled.current.add(key);
  }

  function submit(): void {
    const value = text.trim();
    // In-flight uploads never become parts; wait for them rather than
    // silently dropping an attachment.
    if (!value || isLoadingMessages || drafts.some((d) => d.status === "uploading")) {
      return;
    }
    const parts: BinaryPart[] = drafts.flatMap((d) =>
      d.status === "ready" && d.id !== null && d.url !== null
        ? [
            binaryPart({
              id: d.id,
              mimeType: d.mimeType,
              filename: d.filename,
              url: d.url,
            }),
          ]
        : [],
    );
    const content: string | MessagePart[] = parts.length
      ? [{ type: "text", text: value }, ...parts]
      : value;
    const clear = (): void => {
      setText("");
      setDrafts([]);
    };
    if (isRunning) {
      // Keep the draft when the enqueue fails (e.g. the 422 depth cap).
      void queueStore.enqueue(value, parts).then((ok) => {
        if (ok) clear();
      });
      return;
    }
    void send(content);
    clear();
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
        <AttachmentChips drafts={drafts} onRemove={onRemove} />
        {hint !== null ? (
          <p role="alert" className="mb-1.5 px-1 text-xs text-destructive">
            {hint}
          </p>
        ) : null}
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
          <input
            ref={fileRef}
            type="file"
            multiple
            accept={ATTACH_ACCEPT}
            className="hidden"
            tabIndex={-1}
            aria-hidden="true"
            onChange={onPick}
          />
          <div className="openui-agent-thread-composer__action-bar">
            <IconButton
              onClick={() => fileRef.current?.click()}
              icon={<Paperclip size="1em" />}
              size="extra-small"
              variant="tertiary"
              aria-label="Attach files"
              className="openui-agent-thread-composer__attach-button"
            />
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
