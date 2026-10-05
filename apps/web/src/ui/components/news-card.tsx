import type { ReactNode } from "react";
import { cn } from "cn";
import { Panel, PanelHeader } from "./panel";

// Announcement tile: optional image slot (children), headline, body, link.
// With `onToggle` it is a button surface that opens an overlay - the caller
// owns the overlay, the card only reports the click.
export function NewsCard({
  label,
  title,
  body,
  href,
  linkText = "read more",
  expanded = false,
  onToggle,
  children,
  className,
}: {
  label: string;
  title: string;
  body: string;
  href?: string | undefined;
  linkText?: string | undefined;
  expanded?: boolean;
  onToggle?: (() => void) | undefined;
  children?: ReactNode;
  className?: string;
}): ReactNode {
  const inner = (
    <>
      {children !== undefined && (
        <div className="relative h-32 overflow-hidden border-b border-border">
          {children}
        </div>
      )}
      <div className="flex flex-1 flex-col px-5 py-4">
        <PanelHeader label={label} />
        <h3 className="mt-2 font-display text-lg leading-tight text-foreground">{title}</h3>
        <p className="mt-2 font-mono text-[11px] leading-relaxed text-muted-foreground">{body}</p>
        {onToggle !== undefined && (
          <span className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-foreground">
            release notes +
          </span>
        )}
        {onToggle === undefined && href !== undefined && (
          <a
            href={href}
            className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-foreground underline-offset-4 hover:underline"
          >
            {linkText} -&gt;
          </a>
        )}
      </div>
    </>
  );

  if (onToggle !== undefined) {
    return (
      <Panel className={cn("flex flex-col transition-all duration-500", className)}>
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={expanded}
          className="flex flex-1 flex-col text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {inner}
        </button>
      </Panel>
    );
  }
  return <Panel className={cn("flex flex-col", className)}>{inner}</Panel>;
}
