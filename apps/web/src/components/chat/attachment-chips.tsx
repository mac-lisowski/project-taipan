"use client";

import { FileText, X } from "lucide-react";
import type { ReactNode } from "react";

import type { AttachmentDraft } from "@/lib/attachments";

type AttachmentChipsProps = {
  drafts: AttachmentDraft[];
  onRemove: (key: string) => void;
};

const chipClass =
  "flex min-w-0 items-center gap-1.5 rounded-lg border border-border bg-background py-1 pl-1.5 pr-1 text-xs";
const removeClass =
  "rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground";

// Draft attachments above the composer input: image rows get a content-
// URL thumbnail, other mimes a file icon; failed uploads are flagged and
// stay removable. Sent rows clear with the draft (the message owns them).
export function AttachmentChips({
  drafts,
  onRemove,
}: AttachmentChipsProps): ReactNode {
  if (drafts.length === 0) return null;
  return (
    <ul className="mb-1.5 flex flex-wrap gap-1.5">
      {drafts.map((draft) => (
        <li
          key={draft.key}
          className={`${chipClass} ${
            draft.status === "failed" ? "border-destructive/50" : ""
          }`}
        >
          {draft.status === "ready" &&
          draft.url !== null &&
          draft.mimeType.startsWith("image/") ? (
            // next/image proxies without the session cookie; /api/files
            // content needs it, so a plain <img> is required.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={draft.url}
              alt={draft.filename}
              className="h-7 w-7 rounded object-cover"
            />
          ) : (
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <span className="max-w-32 truncate" title={draft.filename}>
            {draft.filename}
          </span>
          {draft.status === "uploading" ? (
            <span className="shrink-0 text-muted-foreground italic">
              uploading…
            </span>
          ) : null}
          {draft.status === "failed" ? (
            <span className="shrink-0 text-destructive">failed</span>
          ) : null}
          <button
            type="button"
            className={removeClass}
            onClick={() => onRemove(draft.key)}
            aria-label={`Remove ${draft.filename}`}
          >
            <X className="h-3 w-3" />
          </button>
        </li>
      ))}
    </ul>
  );
}
