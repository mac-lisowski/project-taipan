"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import type { DocGroup } from "@/lib/docs";
import { cn } from "cn";

// Sidebar nav: grouped by section, active page gets a signal left edge.
// Client so usePathname can mark the current doc.
export function DocsNav({ groups }: { groups: DocGroup[] }): ReactNode {
  const pathname = usePathname();

  return (
    <nav className="mt-6 flex flex-col gap-5">
      {groups.map((group) => (
        <div key={group.section}>
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
            {group.section}
          </p>
          <div className="mt-1.5 flex flex-col gap-0.5">
            {group.entries.map((doc) => {
              const href = `/docs/${doc.slug.join("/")}`;
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "truncate border-l py-1 pl-3 font-mono text-[11px] transition-colors",
                    active
                      ? "border-signal text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  {doc.title}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}
