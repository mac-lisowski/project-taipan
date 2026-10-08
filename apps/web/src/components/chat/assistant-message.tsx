"use client";

import { MarkDownRenderer, type AssistantMessage } from "@openuidev/react-ui";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";

// Default assistant path skips remark-gfm; no tools are wired, so no timeline here.
export function AssistantMessage({
  message,
}: {
  message: AssistantMessage;
}): ReactNode {
  return (
    <div className="openui-agent-thread-message-assistant">
      <div className="openui-agent-thread-message-assistant__content">
        <MarkDownRenderer
          textMarkdown={message.content ?? ""}
          className="openui-agent-thread-message-assistant__text"
          options={{ remarkPlugins: [[remarkGfm, { singleTilde: false }]] }}
        />
      </div>
    </div>
  );
}
