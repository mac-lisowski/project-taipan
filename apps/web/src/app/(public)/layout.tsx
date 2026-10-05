import Link from "next/link";
import { ViewTransition } from "react";
import type { ReactNode } from "react";
import { Panel } from "@/ui";

const GITHUB_URL = "https://github.com/mac-lisowski/project-taipan";

function GithubMark(): ReactNode {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className="size-3.5 fill-current">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

// Shared shell for public routes: background layers, wordmark panel,
// license strip. Only the children slot swaps between pages.
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6">
      <div aria-hidden="true" className="bg-loop pointer-events-none fixed inset-0" />
      <div aria-hidden="true" className="grain pointer-events-none fixed inset-0" />
      <Panel
        ticks
        className="flex w-full max-w-3xl flex-col gap-8 px-10 py-8 sm:flex-row sm:items-center"
      >
        <Link
          href="/"
          className="group/mark block shrink-0 outline-none sm:border-r sm:border-border sm:pr-8"
        >
          <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
            project
          </p>
          <h1 className="font-display mt-3 text-5xl uppercase leading-none tracking-tight text-foreground transition-colors group-hover/mark:text-signal group-focus-visible/mark:text-signal">
            taipan
          </h1>
        </Link>
        <ViewTransition>
          <div className="flex w-full flex-1 flex-col">{children}</div>
        </ViewTransition>
      </Panel>

      <div className="flex w-full max-w-3xl items-center justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground/60">
        <span>mit license</span>
        <div className="flex items-center gap-5">
          <Link
            href="/docs"
            className="underline-offset-4 transition-colors hover:text-foreground hover:underline"
          >
            docs
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub repository"
            className="flex items-center gap-1.5 transition-colors hover:text-foreground"
          >
            <GithubMark />
            github
          </a>
        </div>
      </div>
    </main>
  );
}
