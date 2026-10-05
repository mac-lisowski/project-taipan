"use client";

import { useEffect, useState, type ReactNode } from "react";

// Top status bar + footer strip: real clock and build stamp sell "ops
// console" - evidence that someone ships this thing.
export function StatusBar(): ReactNode {
  const [now, setNow] = useState("");
  useEffect(() => {
    const tick = () => {
      setNow(new Date().toISOString().slice(11, 19));
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => {
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-40 flex items-center justify-between px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
      <span>taipan</span>
      <span suppressHydrationWarning>{now} utc</span>
      <span>v0.1.0</span>
    </div>
  );
}

export function Footer(): ReactNode {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex items-center justify-between px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground/60">
      <span>taipan.dev</span>
      <span>build dev · esc to close</span>
      <span>up 41d</span>
    </div>
  );
}
