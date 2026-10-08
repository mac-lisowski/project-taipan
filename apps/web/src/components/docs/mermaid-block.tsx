"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    background: "#0a0a0b",
    primaryColor: "#1a1a1c",
    primaryTextColor: "#e5e5e5",
    primaryBorderColor: "#3f3f46",
    lineColor: "#71717a",
    fontFamily: "monospace",
  },
});

let counter = 0;

// Renders a mermaid diagram source block to SVG on mount.
export function MermaidBlock({ code }: { code: string }): ReactNode {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const id = `mmd-${counter++}`;
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <pre className="overflow-x-auto border border-border bg-background/80 p-3 font-mono text-[10px] text-muted-foreground">
        {code}
      </pre>
    );
  }
  return <div ref={ref} className="overflow-x-auto [&_svg]:max-w-full" />;
}
