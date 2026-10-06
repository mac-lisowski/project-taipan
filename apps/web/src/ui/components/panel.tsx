import type { ReactNode } from "react";
import { cn } from "cn";

// Signature surface: 1px border, translucent over the dither. Corner
// ticks are rationed to hero surfaces - pass ticks on focal panels only.
export function Panel({
  ticks = false,
  className,
  children,
}: {
  ticks?: boolean;
  className?: string;
  children: ReactNode;
}): ReactNode {
  const tick =
    "absolute size-2 border-zinc-300 transition-colors duration-300 group-hover/panel:border-signal";
  return (
    <div
      className={cn(
        "group/panel relative border border-border bg-background/70 backdrop-blur-sm transition-colors duration-300 hover:border-foreground/30",
        className,
      )}
    >
      {ticks && (
        <>
          <span aria-hidden="true" className={cn(tick, "-left-px -top-px border-l border-t")} />
          <span aria-hidden="true" className={cn(tick, "-right-px -top-px border-r border-t")} />
          <span aria-hidden="true" className={cn(tick, "-bottom-px -left-px border-b border-l")} />
          <span aria-hidden="true" className={cn(tick, "-bottom-px -right-px border-b border-r")} />
        </>
      )}
      {children}
    </div>
  );
}

export function PanelHeader({
  label,
  className,
}: {
  label: string;
  className?: string;
}): ReactNode {
  return (
    <p className={cn("font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground", className)}>
      {label}
    </p>
  );
}
