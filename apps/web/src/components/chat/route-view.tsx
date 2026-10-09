"use client";

import type { ReactNode } from "react";

// App views share the chat's own scroll frame so they read as one design.
// The mobile row is the only way out of a route on small screens: the SDK
// renders no mobile header on route views.
export function RouteView({
  children,
  onExit,
}: {
  children: ReactNode;
  onExit: () => void;
}): ReactNode {
  return (
    <div className="openui-agent-thread-scroll-area">
      {/* Same 880px column the SDK gives chat messages, so all views match. */}
      <div className="mx-auto flex w-full max-w-[calc(880px+2*var(--openui-space-m-l))] flex-col px-[var(--openui-space-m-l)] py-8">
        <button
          type="button"
          onClick={onExit}
          className="self-start rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:hidden"
        >
          &larr; chat
        </button>
        {children}
      </div>
    </div>
  );
}
