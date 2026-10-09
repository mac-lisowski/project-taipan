import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { readSharedThread } from "@/app/api/public/read-share";
import { SharedMessage } from "@/components/chat/shared-message";

// Share links carry a private transcript; keep them out of indexes.
// next.config.ts adds the X-Robots-Tag header on the same route.
export const metadata: Metadata = {
  title: "shared thread",
  robots: { index: false, follow: false },
};

// Read-only transcript of a frozen snapshot. A dead token is a real
// 404; a failed read is an honest error, not a fake 404.
export default async function SharePage({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<ReactNode> {
  const { token } = await params;
  const result = await readSharedThread(token);
  if (!result.ok && result.kind === "not-found") notFound();
  if (!result.ok) {
    return (
      <p
        role="alert"
        className="font-mono text-[10px] tracking-[0.15em] text-red-400"
      >
        err: shared transcript is unavailable right now
      </p>
    );
  }
  const { title, messages } = result.data;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
          shared thread
        </p>
        <h2 className="font-display text-xl uppercase leading-tight tracking-tight text-foreground">
          {title}
        </h2>
      </div>
      {messages.length === 0 ? (
        <p className="font-mono text-[11px] text-muted-foreground">
          this transcript is empty
        </p>
      ) : (
        <ol className="flex flex-col gap-5">
          {messages.map((message, index) => (
            <li key={index}>
              {typeof message.content !== "string" ? (
                // Snapshots can carry OpenAI parts arrays; a transcript
                // must still render rather than fall into the error view.
                <p className="font-mono text-[11px] italic text-muted-foreground">
                  [unsupported message content]
                </p>
              ) : message.role === "assistant" ? (
                <SharedMessage content={message.content} />
              ) : (
                <div className="openui-agent-thread-message-user">
                  <div className="openui-agent-thread-message-user__content">
                    {message.content}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
