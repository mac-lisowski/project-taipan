"use client";

import { useEffect, useId, useState, type ReactNode } from "react";

import { useThemeMode } from "@/lib/use-theme";

// One global mermaid instance; re-init only when the mode flips so the
// SVG colors follow the app palette (neutral on light, dark on dark).
let initializedTheme: string | null = null;

// Result of the last render attempt, keyed to its source text: an attempt
// for older code is ignored, so no effect-body state resets are needed.
type Outcome = { code: string; svg: string | null };

// Fenced ```mermaid blocks stream in partially and fail to parse; the raw
// source stands in until the diagram closes and renders.
export function MermaidDiagram({ code }: { code: string }): ReactNode {
  const dark = useThemeMode() === "dark";
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const renderId = `mermaid-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  const current = outcome !== null && outcome.code === code;
  const svg = current ? outcome.svg : null;
  const failed = current && outcome.svg === null;

  useEffect(() => {
    let cancelled = false;
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
          if (!cancelled) setOutcome({ code, svg: next });
        } catch {
          if (!cancelled) setOutcome({ code, svg: null });
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
