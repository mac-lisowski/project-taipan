"use client";

import { MarkDownRenderer } from "@openuidev/react-ui";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";

// remarkPlugins hold functions, so a server component cannot pass the
// options object; the snapshot content crosses the boundary as a plain
// string. Mirrors assistant-message.tsx, same gfm options.
export function SharedMessage({ content }: { content: string }): ReactNode {
  return (
    <div className="openui-agent-thread-message-assistant">
      <div className="openui-agent-thread-message-assistant__content">
        <MarkDownRenderer
          textMarkdown={content}
          className="openui-agent-thread-message-assistant__text"
          options={{ remarkPlugins: [[remarkGfm, { singleTilde: false }]] }}
        />
      </div>
    </div>
  );
}
