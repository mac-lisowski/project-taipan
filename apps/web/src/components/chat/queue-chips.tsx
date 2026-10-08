"use client";

import { ArrowUp, Check, Pencil, X } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { ChatQueueSnapshot, QueueRow } from "@/lib/chat-queue";

type QueueChipsProps = {
  queue: ChatQueueSnapshot;
  /** Idle thread: the head chip offers a manual send. */
  canSendHead: boolean;
  onEdit: (id: string, text: string) => void;
  onRemove: (id: string) => void;
  onSendHead: () => void;
};

const chipClass =
  "flex max-w-full items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs";
const iconBtnClass =
  "rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground";

// One queued message; a row being dispatched is locked so its text cannot
// shift mid-run.
function QueueChip({
  row,
  isHead,
  failed,
  sending,
  canSendHead,
  onEdit,
  onRemove,
  onSendHead,
}: {
  row: QueueRow;
  isHead: boolean;
  failed: boolean;
  sending: boolean;
  canSendHead: boolean;
  onEdit: (id: string, text: string) => void;
  onRemove: (id: string) => void;
  onSendHead: () => void;
}): ReactNode {
  const [draft, setDraft] = useState<string | null>(null);

  function saveEdit(): void {
    const next = (draft ?? "").trim();
    setDraft(null);
    if (next && next !== row.content.text) onEdit(row.id, next);
  }

  if (draft !== null) {
    return (
      <li className={chipClass}>
        <input
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") saveEdit();
            if (e.key === "Escape") setDraft(null);
          }}
          className="w-40 bg-transparent text-xs outline-none"
          aria-label="Edit queued message"
        />
        <button type="button" className={iconBtnClass} onClick={saveEdit} aria-label="Save edit">
          <Check className="h-3 w-3" />
        </button>
        <button
          type="button"
          className={iconBtnClass}
          onClick={() => setDraft(null)}
          aria-label="Cancel edit"
        >
          <X className="h-3 w-3" />
        </button>
      </li>
    );
  }

  if (sending) {
    return (
      <li className={`${chipClass} text-muted-foreground`}>
        <span className="truncate">{row.content.text}</span>
        <span className="shrink-0 italic">sending…</span>
      </li>
    );
  }

  return (
    <li className={`${chipClass} ${failed ? "border-destructive/50" : ""}`}>
      {isHead && (failed || canSendHead) ? (
        <button
          type="button"
          className={`${iconBtnClass} ${failed ? "text-destructive" : ""}`}
          onClick={onSendHead}
          aria-label="Send queued message"
          title={failed ? "Send failed - send now" : "Send now"}
        >
          <ArrowUp className="h-3 w-3" />
        </button>
      ) : null}
      <span className="truncate" title={row.content.text}>
        {row.content.text}
      </span>
      {failed ? <span className="shrink-0 text-destructive">failed</span> : null}
      <button
        type="button"
        className={iconBtnClass}
        onClick={() => setDraft(row.content.text)}
        aria-label="Edit queued message"
      >
        <Pencil className="h-3 w-3" />
      </button>
      <button
        type="button"
        className={iconBtnClass}
        onClick={() => onRemove(row.id)}
        aria-label="Remove queued message"
      >
        <X className="h-3 w-3" />
      </button>
    </li>
  );
}

// Chips above the composer mirror the server-side queue; a failed or
// idle head offers a manual send.
export function QueueChips({
  queue,
  canSendHead,
  onEdit,
  onRemove,
  onSendHead,
}: QueueChipsProps): ReactNode {
  if (queue.rows.length === 0 && queue.notice === null) return null;
  return (
    <div className="mb-1.5">
      {queue.rows.length > 0 ? (
        <ul className="flex max-h-20 flex-wrap gap-1.5 overflow-y-auto">
          {queue.rows.map((row, index) => (
            <QueueChip
              key={row.id}
              row={row}
              isHead={index === 0}
              failed={queue.failedId === row.id}
              sending={queue.dispatch?.id === row.id}
              canSendHead={canSendHead && queue.dispatch === null}
              onEdit={onEdit}
              onRemove={onRemove}
              onSendHead={onSendHead}
            />
          ))}
        </ul>
      ) : null}
      {queue.notice !== null ? (
        <p className="pt-1 text-xs text-destructive">
          {queue.notice === "enqueue-failed"
            ? "Could not queue the message. The queue may be full."
            : "Queue out of sync with the server."}
        </p>
      ) : null}
    </div>
  );
}
