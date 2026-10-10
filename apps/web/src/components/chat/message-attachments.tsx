"use client";

import type {
  BinaryInputContent,
  UserMessage as UserMessageType,
} from "@openuidev/react-headless";
import type { ReactNode } from "react";

// Stored dicts are client-supplied; only same-origin paths or http(s) reach the anchor.
const SAFE_HREF = /^\/(?!\/|^$)|^https?:\/\//i;

// A binary part is a file reference: url is the proxied route, id its registry row.
function attachmentHref(part: BinaryInputContent): string | undefined {
  if (typeof part.url === "string" && SAFE_HREF.test(part.url)) {
    return part.url;
  }
  if (typeof part.id === "string" && part.id !== "") {
    return `/api/files/${encodeURIComponent(part.id)}/content`;
  }
  return undefined;
}

function badge(mimeType: string): string {
  if (mimeType.includes("pdf")) return "PDF";
  if (mimeType.startsWith("text/")) return "TXT";
  return "FILE";
}

function AttachmentPart({ part }: { part: BinaryInputContent }): ReactNode {
  const href = attachmentHref(part);
  const name = part.filename ?? part.mimeType;
  if (part.mimeType.startsWith("image/") && href !== undefined) {
    return (
      // Session-proxied content route; next/image cannot optimize it.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={href}
        alt={name}
        loading="lazy"
        className="openui-agent-thread-message-user__image"
      />
    );
  }
  const chip = (
    <span className="openui-agent-thread-message-user__chip">
      <span
        className="openui-agent-thread-message-user__chip-badge"
        aria-hidden="true"
      >
        {badge(part.mimeType)}
      </span>
      <span className="openui-agent-thread-message-user__chip-name">{name}</span>
    </span>
  );
  if (href === undefined) return chip;
  return (
    <a
      href={href}
      download={part.filename ?? ""}
      target="_blank"
      rel="noreferrer"
      aria-label={`Download ${name}`}
      className="openui-agent-thread-message-user__chip-link"
    >
      {chip}
    </a>
  );
}

// The SDK default renders binary parts but has no registry-id fallback.
export function UserMessage({
  message,
}: {
  message: UserMessageType;
}): ReactNode {
  const { content } = message;
  return (
    <div className="openui-agent-thread-message-user">
      <div className="openui-agent-thread-message-user__content">
        {typeof content === "string"
          ? content
          : content?.map((part, i) => {
              if (part.type === "binary") {
                return <AttachmentPart key={i} part={part} />;
              }
              if (part.type === "text" && part.text.trim() !== "") {
                return (
                  <span
                    key={i}
                    className="openui-agent-thread-message-user__text"
                  >
                    {part.text}
                  </span>
                );
              }
              return null;
            })}
      </div>
    </div>
  );
}
