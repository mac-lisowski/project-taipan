"use client";

import { ArrowUp, Check, ListOrdered, Pencil, X } from "lucide-react";
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

const rowClass =
  "flex min-w-0 items-center gap-2 rounded-lg border border-border bg-background px-2 py-1.5 text-xs";
const iconBtnClass =
  "rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground";
const badgeClass =
  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium tabular-nums";

// One queued message; a row being dispatched is locked so its text cannot
// shift mid-run.
function QueueRowItem({
  row,
  position,
  isHead,
  failed,
  sending,
  canSendHead,
  onEdit,
  onRemove,
  onSendHead,
}: {
  row: QueueRow;
  position: number;
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

  const sendNow =
    isHead && (failed || canSendHead) ? (
      <button
        type="button"
        className={`${iconBtnClass} ${failed ? "text-destructive" : ""}`}
        onClick={onSendHead}
        aria-label="Send queued message"
        title={failed ? "Send failed - send now" : "Send now"}
      >
        <ArrowUp className="h-3 w-3" />
      </button>
    ) : null;

  if (draft !== null) {
    return (
      <li className={rowClass}>
        {sendNow}
        <input
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") saveEdit();
            if (e.key === "Escape") setDraft(null);
          }}
          className="min-w-0 flex-1 bg-transparent outline-none"
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
      <li className={`${rowClass} text-muted-foreground`}>
        <span className={badgeClass}>{position}</span>
        <span className="min-w-0 flex-1 truncate">{row.content.text}</span>
        <span className="shrink-0 italic">sending…</span>
      </li>
    );
  }

  return (
    <li className={`${rowClass} ${failed ? "border-destructive/50" : ""}`}>
      {sendNow}
      <span className={badgeClass}>{position}</span>
      <span className="min-w-0 flex-1 truncate" title={row.content.text}>
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

// Panel above the composer input mirrors the server-side queue; a failed or
// idle head offers a manual send. The list scrolls past a few rows.
export function QueueChips({
  queue,
  canSendHead,
  onEdit,
  onRemove,
  onSendHead,
}: QueueChipsProps): ReactNode {
  if (queue.rows.length === 0 && queue.notice === null) return null;
  return (
    <div className="mb-2 rounded-xl border border-border bg-muted/40 p-1.5">
      {queue.rows.length > 0 ? (
        <>
          <div className="flex items-center gap-1.5 px-1.5 pb-1 pt-0.5 text-[11px] font-medium text-muted-foreground">
            <ListOrdered className="h-3 w-3" />
            Queued
            <span className="rounded-full bg-muted px-1.5 text-[10px] tabular-nums">
              {queue.rows.length}
            </span>
          </div>
          <ul className="flex max-h-40 flex-col gap-1 overflow-y-auto">
            {queue.rows.map((row, index) => (
              <QueueRowItem
                key={row.id}
                row={row}
                position={index + 1}
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
        </>
      ) : null}
      {queue.notice !== null ? (
        <p className="px-1.5 pt-1 text-xs text-destructive">
          {queue.notice === "enqueue-failed"
            ? "Could not queue the message. The queue may be full."
            : "Queue out of sync with the server."}
        </p>
      ) : null}
    </div>
  );
}
