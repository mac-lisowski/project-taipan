import Link from "next/link";
import { ViewTransition } from "react";
import type { ReactNode } from "react";
import { listDocGroups } from "@/lib/docs";
import { DocsNav } from "@/components/docs/docs-nav";

// Docs shell: own layout outside the auth panel - grouped sidebar on the
// left, content on the right. Same dark surface language.
export default async function DocsLayout({ children }: { children: ReactNode }) {
  const groups = await listDocGroups();

  return (
    <main className="relative min-h-screen bg-background">
      <div aria-hidden="true" className="bg-loop pointer-events-none fixed inset-0" />
      <div className="relative mx-auto flex max-w-6xl gap-10 px-6 py-10">
        <aside className="w-56 shrink-0">
          <Link
            href="/"
            className="font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground transition-colors hover:text-foreground"
          >
            {"<- taipan"}
          </Link>
          <p className="font-display mt-4 text-xl uppercase text-foreground">docs</p>
          <DocsNav groups={groups} />
        </aside>
        <div className="min-w-0 flex-1 border-l border-border pl-10">
          <ViewTransition>{children}</ViewTransition>
        </div>
      </div>
    </main>
  );
}
