import type { ReactNode } from "react";
import { cn } from "cn";
import { Panel, PanelHeader } from "./panel";

// KPI tile: label, big value, optional signed delta (up = bright, down = dim).
export function Stat({
  label,
  value,
  delta,
  className,
}: {
  label: string;
  value: string;
  delta?: string | undefined;
  className?: string;
}): ReactNode {
  const negative = delta?.startsWith("-") ?? false;
  return (
    <Panel className={cn("px-5 py-4", className)}>
      <PanelHeader label={label} />
      <p className="mt-2 font-display text-3xl leading-none text-foreground">{value}</p>
      {delta !== undefined && (
        <p className={cn("mt-2 font-mono text-[10px] tracking-[0.15em]", negative ? "text-muted-foreground" : "text-signal")}>
          {delta}
        </p>
      )}
    </Panel>
  );
}
