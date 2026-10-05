"use client";

import { useState, type ReactNode } from "react";
import { cn } from "cn";

export interface CodeTab {
  readonly id: string;
  readonly label: string;
  readonly code: string;
  readonly lang?: "python" | "typescript" | "http" | undefined;
}

// Minimal highlighter for our snippet vocab: comments, strings, keywords,
// numbers. Not a parser - regex classes are enough at this scale.
const KEYWORDS: Record<string, readonly string[]> = {
  python: ["import", "from", "def", "return", "as", "with", "for", "in", "if", "else", "print"],
  typescript: ["const", "let", "await", "async", "function", "return", "import", "from", "new", "process"],
  http: ["GET", "POST", "PUT", "DELETE", "PATCH"],
};

const TOKEN_RE =
  /(#[^\n]*|\/\/[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/g;

function highlight(code: string, lang: CodeTab["lang"]): ReactNode {
  const keywords = new Set(lang !== undefined ? (KEYWORDS[lang] ?? []) : []);
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of code.matchAll(TOKEN_RE)) {
    if (m.index > last) out.push(code.slice(last, m.index));
    const [text, comment, str, num, word] = m;
    let cls = "text-muted-foreground";
    if (comment !== undefined) cls = "text-zinc-600";
    else if (str !== undefined) cls = "text-emerald-200/80";
    else if (num !== undefined) cls = "text-zinc-300";
    else if (word !== undefined && keywords.has(word)) cls = "text-foreground";
    out.push(
      <span key={key++} className={cls}>
        {text}
      </span>,
    );
    last = m.index + text.length;
  }
  if (last < code.length) out.push(code.slice(last));
  return out;
}

// Terminal-window code block: tab strip in the top border, copy button at
// the right edge, one highlighted mono <pre> body.
export function CodeTabs({
  tabs,
  className,
}: {
  tabs: readonly CodeTab[];
  className?: string;
}): ReactNode {
  const [active, setActive] = useState(tabs[0]?.id);
  const [copied, setCopied] = useState(false);
  const current = tabs.find((t) => t.id === active) ?? tabs[0];

  const copy = async () => {
    if (current === undefined) return;
    try {
      await navigator.clipboard.writeText(current.code);
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
      }, 1500);
    } catch {
      // clipboard unavailable (non-secure context): leave state untouched
    }
  };

  return (
    <div className={cn("border border-border bg-background/80", className)}>
      <div className="flex items-center border-b border-border" role="tablist">
        {tabs.map((tab) => {
          const selected = tab.id === current?.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => {
                setActive(tab.id);
              }}
              className={cn(
                "border-r border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] transition-colors outline-none focus-visible:bg-secondary",
                selected
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => {
            void copy();
          }}
          className={cn(
            "ml-auto px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] transition-colors hover:text-foreground",
            copied ? "text-signal" : "text-muted-foreground",
          )}
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[10px] leading-relaxed">
        {current !== undefined && highlight(current.code, current.lang)}
      </pre>
    </div>
  );
}
