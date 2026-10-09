"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore, type ReactNode } from "react";
import { LogoutButton } from "@/components/auth/logout-button";
import { sidebarOpenStore, writeSidebarOpen } from "@/components/shell/sidebar-state";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import {
  ShellAccountProvider,
  ShellThreadsProvider,
  type ShellAccount,
} from "@/components/shell/shell-context";
import type { ThreadSeed } from "@/lib/chat-config";
import { CHAT_SURFACE_ROUTES, privateNav, type NavItem } from "@/lib/nav";

function GearIcon(): ReactNode {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="inline-block h-3 w-3 align-[-2px]"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function UsersIcon(): ReactNode {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="inline-block h-3 w-3 align-[-2px]"
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function NavItemLink({ item, active }: { item: NavItem; active: boolean }): ReactNode {
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`font-mono text-[11px] tracking-[0.15em] px-3 py-2 transition-colors hover:text-foreground ${
        active ? "bg-accent text-foreground" : "text-muted-foreground"
      }`}
    >
      {item.icon === "gear" && <GearIcon />} {item.icon === "users" && <UsersIcon />} {item.label}
    </Link>
  );
}

// Collapsible sidebar shell for private routes. Open state persists in
// localStorage; the header toggle stays visible so a closed bar reopens.
export function PrivateShell({
  id,
  email,
  tenant,
  roles,
  systemRoles,
  threads,
  children,
}: {
  id: number;
  email: string;
  tenant: string;
  roles: string[];
  systemRoles: string[];
  threads: ThreadSeed | null;
  children: ReactNode;
}): ReactNode {
  const pathname = usePathname() ?? "";
  const open = useSyncExternalStore(
    sidebarOpenStore.subscribe,
    sidebarOpenStore.getSnapshot,
    sidebarOpenStore.getServerSnapshot,
  );
  const sections = privateNav(systemRoles);
  const account: ShellAccount = { id, email, tenant, roles, systemRoles };

  // The chat app (chat + its route views) is a full-viewport OpenUI surface
  // with its own sidebar; the shell stays out of the way and only hands
  // over the session identity plus the server-fetched thread seed.
  if (CHAT_SURFACE_ROUTES.includes(pathname)) {
    return (
      <ShellAccountProvider account={account}>
        <ShellThreadsProvider threads={threads}>
          <div className="h-dvh w-full overflow-hidden bg-background">{children}</div>
        </ShellThreadsProvider>
      </ShellAccountProvider>
    );
  }

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
            {sections.map((section) => (
              <div
                key={section.heading ?? "main"}
                className="flex flex-row gap-1 md:flex-col"
              >
                {section.heading && (
                  <p className="px-3 pt-3 font-mono text-[10px] tracking-[0.35em] text-muted-foreground md:pt-2">
                    {section.heading}
                  </p>
                )}
                {section.items.map((item) => {
                  const active =
                    pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return <NavItemLink key={item.href} item={item} active={active} />;
                })}
              </div>
            ))}
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
          <ThemeToggle />
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
