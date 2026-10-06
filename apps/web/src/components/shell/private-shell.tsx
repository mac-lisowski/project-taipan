"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore, type ReactNode } from "react";
import { LogoutButton } from "@/components/auth/logout-button";
import { sidebarOpenStore, writeSidebarOpen } from "@/components/shell/sidebar-state";

const NAV = [
  { href: "/dashboard", label: "dashboard" },
  { href: "/account", label: "account" },
  { href: "/docs", label: "docs" },
] as const;

// Collapsible sidebar shell for private routes. Open state persists in
// localStorage; the header toggle stays visible so a closed bar reopens.
export function PrivateShell({
  email,
  tenant,
  children,
}: {
  email: string;
  tenant: string;
  children: ReactNode;
}): ReactNode {
  const pathname = usePathname() ?? "";
  const open = useSyncExternalStore(
    sidebarOpenStore.subscribe,
    sidebarOpenStore.getSnapshot,
    sidebarOpenStore.getServerSnapshot,
  );

  return (
    <div className="flex min-h-screen flex-col bg-background md:flex-row">
      {open && (
        <aside
          id="private-sidebar"
          className="flex shrink-0 flex-col border-b border-border bg-card md:w-60 md:border-b-0 md:border-r"
        >
          <p className="border-b border-border px-5 py-4">
            <span className="block font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
              project
            </span>
            <span className="font-display mt-1 block text-2xl uppercase leading-none tracking-tight">
              taipan
            </span>
          </p>
          <nav aria-label="Private" className="flex flex-row gap-1 p-3 md:flex-col">
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`font-mono text-[11px] tracking-[0.15em] px-3 py-2 transition-colors hover:text-foreground ${
                    active
                      ? "bg-accent text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto hidden border-t border-border p-4 md:block">
            <p className="truncate font-mono text-[11px] text-foreground">{email}</p>
            <p className="mt-1 break-all font-mono text-[10px] text-muted-foreground">
              {tenant}
            </p>
            <div className="mt-2">
              <LogoutButton />
            </div>
          </div>
        </aside>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-border px-4 py-2">
          <button
            type="button"
            onClick={() => writeSidebarOpen(!open)}
            aria-expanded={open}
            aria-controls="private-sidebar"
            className="border border-border px-2 py-1 font-mono text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {open ? "hide menu" : "show menu"}
          </button>
          <p className="truncate font-mono text-[10px] tracking-[0.2em] text-muted-foreground md:hidden">
            {email}
          </p>
          <div className="ml-auto md:hidden">
            <LogoutButton />
          </div>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
