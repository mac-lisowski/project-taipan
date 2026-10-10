"use client";

import { MarkDownRenderer, type AssistantMessage } from "@openuidev/react-ui";
import remarkGfm from "remark-gfm";
import { isValidElement, type ReactNode } from "react";
import type { Components } from "react-markdown";

import { MermaidDiagram } from "@/components/chat/mermaid-block";

// Mermaid fences arrive as SDK CodeBlock elements; swap them for a rendered diagram.
const components: Components = {
  pre({ children }) {
    const child = Array.isArray(children) ? children[0] : children;
    const props = isValidElement(child)
      ? (child.props as { language?: string; codeString?: unknown })
      : null;
    if (props?.language === "mermaid") {
      return <MermaidDiagram code={String(props.codeString ?? "")} />;
    }
    return <pre>{children}</pre>;
  },
};

// Default assistant path skips remark-gfm; tool activity lives in the SDK
// timeline around this slot, not inside the message body.
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
          options={{ remarkPlugins: [[remarkGfm, { singleTilde: false }]], components }}
        />
      </div>
    </div>
  );
}
