"use client";

import { useEffect, useId, useState, type ReactNode } from "react";

import { useThemeMode } from "@/lib/use-theme";

// One global mermaid instance; re-init only when the mode flips so the
// SVG colors follow the app palette (neutral on light, dark on dark).
let initializedTheme: string | null = null;

// Fenced ```mermaid blocks stream in partially and fail to parse; the raw
// source stands in until the diagram closes and renders.
export function MermaidDiagram({ code }: { code: string }): ReactNode {
  const dark = useThemeMode() === "dark";
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const renderId = `mermaid-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    // Streams append tokens faster than diagrams can lay out; render settled code only.
    const timer = setTimeout(() => {
      void (async () => {
        const { default: mermaid } = await import("mermaid");
        const theme = dark ? "dark" : "neutral";
        if (initializedTheme !== theme) {
          // suppressErrorRendering keeps failed parses from leaking an error
          // SVG into the page; we show our own fallback.
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: "strict",
            suppressErrorRendering: true,
            theme,
          });
          initializedTheme = theme;
        }
        try {
          const { svg: next } = await mermaid.render(renderId, code);
          if (!cancelled) setSvg(next);
        } catch {
          if (!cancelled) setFailed(true);
        }
      })();
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [code, dark, renderId]);

  if (failed) {
    return (
      <pre className="overflow-x-auto rounded-xl border border-border bg-muted/40 p-3 text-xs">
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div
      className="flex justify-center overflow-x-auto rounded-xl border border-border bg-background py-3 [&_svg]:h-auto [&_svg]:max-w-full"
      {...(svg === null
        ? {}
        : { dangerouslySetInnerHTML: { __html: svg } })}
    >
      {svg === null ? (
        <span className="py-6 text-xs text-muted-foreground">Rendering diagram…</span>
      ) : null}
    </div>
  );
}
