"use client";

import Image from "next/image";
import { useEffect, useState, type ReactNode } from "react";
import { CodeTabs, NewsCard, Panel, PanelHeader, Stat, cn } from "@/ui";
import { LiveStats } from "@/components/live-stats";

// Expanded release renders as a fixed overlay: the grid never reflows,
// siblings only fade into the backdrop.
const dimmed = "opacity-15 blur-[2px] saturate-0 pointer-events-none select-none";

function ReleaseOverlay({ onClose }: { onClose: () => void }): ReactNode {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      aria-label="taipan-small-json release notes"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl animate-[release-in_0.35s_ease-out]"
        onClick={(e) => {
          e.stopPropagation();
        }}
      >
        <Panel ticks className="flex flex-col">
          <div className="relative h-64 overflow-hidden border-b border-border">
            <Image
              src="/taipan-small-json-preview.webp"
              alt="Taipan snake rendered in dithered dots"
              fill
              className="object-cover"
            />
          </div>
          <div className="flex flex-col gap-4 px-6 py-5">
            <PanelHeader label="release" />
            <h3 className="font-display text-2xl leading-tight text-foreground">
              taipan-small-json
            </h3>
            <ul className="grid grid-cols-2 gap-x-6 gap-y-2 font-mono text-[11px] text-muted-foreground sm:grid-cols-4">
              <li><span className="text-foreground">8</span> schemas</li>
              <li><span className="text-foreground">&lt;2 GB</span> RAM</li>
              <li><span className="text-foreground">~1 ms</span> cpu inference</li>
              <li><span className="text-foreground">0</span> gpu required</li>
            </ul>
            <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
              Feed it an issue, a log line, a commit, a pull request, an agent
              tool call, a compiler diagnostic, a diff, or a review comment. A
              learned router picks the schema, token-level extractors fill the
              fields, and you get one validated JSON object per line.
              Multi-line streams and stack traces stay attached to their
              parent record. Need a shape we do not ship? Register your own
              schema and the router learns to route to it.
            </p>
            <CodeTabs
              tabs={[
                {
                  id: "python",
                  label: "python",
                  lang: "python",
                  code: `import httpx

res = httpx.post(
    "https://api.taipan.dev/v1/classify",
    headers={"Authorization": "Bearer $TAIPAN_KEY"},
    json={"text": "ERROR [auth]: token expired"},
)
obj = res.json()["obj"]
# {"type": "log_event", "level": "ERROR",
#  "component": "auth", "message": "token expired"}`,
                },
                {
                  id: "typescript",
                  label: "typescript",
                  lang: "typescript",
                  code: `const res = await fetch("https://api.taipan.dev/v1/classify", {
  method: "POST",
  headers: {
    Authorization: \`Bearer \${process.env.TAIPAN_KEY}\`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ text: "ERROR [auth]: token expired" }),
});
const { obj, meta } = await res.json();
// meta: { routed_by: "model", valid: true, latency_ms: 1.05 }`,
                },
                {
                  id: "schema",
                  label: "custom schema",
                  lang: "http",
                  code: `POST /v1/schemas
{
  "name": "deploy_event",
  "fields": {
    "service": "string",
    "env":     {"enum": ["prod", "staging"]},
    "sha":     {"format": "git-sha"}
  }
}
# then classify with {"schema": "deploy_event", "text": "..."}`,
                },
              ]}
            />
            <button
              type="button"
              onClick={onClose}
              className="self-start font-mono text-[11px] uppercase tracking-[0.15em] text-foreground underline-offset-4 hover:underline"
            >
              close -
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

export function ReleaseGrid(): ReactNode {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className={cn("grid w-full max-w-3xl animate-[release-in_0.6s_ease-out_0.15s_both] grid-cols-1 gap-4 transition-all duration-500 sm:grid-cols-2", open && dimmed)}>
        <NewsCard
          label="release"
          title="taipan-small-json"
          body="First model of the taipan-small family: raw workflow text to strictly valid JSON."
          onToggle={() => {
            setOpen(true);
          }}
        >
          <Image
            src="/taipan-small-json-preview.webp"
            alt="Taipan snake rendered in dithered dots"
            fill
            className="object-cover"
          />
        </NewsCard>
        <div className="grid grid-cols-1 gap-4">
          <Stat label="extractions / day" value="1.2k" delta="+8% / 7d" />
          <Stat label="router p50" value="84ms" delta="-9ms / 7d" />
        </div>
        <LiveStats />
        <Panel className="px-5 py-4">
          <PanelHeader label="status" />
          <ul className="mt-3 flex flex-col gap-2 font-mono text-[11px] text-muted-foreground">
            <li className="flex items-center gap-2">
              <span className="size-1.5 bg-signal" /> api · 23ms p50 · up
            </li>
            <li className="flex items-center gap-2">
              <span className="size-1.5 bg-signal" /> kms · 41d uptime
            </li>
            <li className="flex items-center gap-2">
              <span className="size-1.5 bg-muted-foreground" /> evals · degraded
            </li>
          </ul>
        </Panel>
      </div>
      {open && (
        <ReleaseOverlay
          onClose={() => {
            setOpen(false);
          }}
        />
      )}
    </>
  );
}
