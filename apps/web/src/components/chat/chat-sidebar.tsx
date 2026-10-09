"use client";

import { AgentInterface } from "@openuidev/react-ui";
import { Menu } from "@base-ui/react/menu";
import { ChevronUp, LogOut, Settings2 } from "lucide-react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";

export type ChatSidebarLink = {
  key: string;
  label: string;
  icon: ReactNode;
  // SDK-internal route path; SidebarItem navigates and self-highlights.
  path: string;
};

// Shell brand mark for the header slot. The SDK class carries the collapse
// behavior; no Tailwind display class here or utilities beat its display:none.
export function Brand(): ReactNode {
  return (
    <span className="openui-agent-sidebar-header__agent-name">
      <span className="block font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        project
      </span>
      <span className="mt-1 block font-display text-2xl uppercase leading-none tracking-tight text-foreground">
        taipan
      </span>
    </span>
  );
}

// Collapsed-sidebar mark: the header swaps agentName for this 32px square.
export function TMark(): ReactNode {
  return (
    <span className="openui-agent-sidebar-header__logo flex h-8 w-8 items-center justify-center rounded-lg bg-primary font-display text-base uppercase text-primary-foreground">
      t
    </span>
  );
}

// Inner sidebar content. The parent MUST wrap this in a literal
// <AgentInterface.Sidebar> child: the SDK extracts slots by direct child
// element type and never sees through wrapper components.
export function ChatSidebarContents({
  links,
  email,
  tenant,
  systemRoles,
  openPath,
}: {
  links: ChatSidebarLink[];
  email: string;
  tenant: string;
  systemRoles: string[];
  openPath: (path: string) => void;
}): ReactNode {
  const router = useRouter();

  // POST, not GET: a GET /logout fires on prefetch and kills the session.
  function logout(): void {
    void fetch("/logout", { method: "POST" }).finally(() => {
      router.push("/");
      router.refresh();
    });
  }

  const menuItem =
    "flex cursor-default items-center gap-2.5 rounded-md px-3 py-2 text-sm text-popover-foreground data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground";

  return (
    <>
      <div className="openui-agent-sidebar-actions">
        <AgentInterface.SidebarHeader logo={<TMark />} agentName={<Brand />} />
        <div className="openui-agent-sidebar-primary-actions">
          <AgentInterface.NewChatButton />
        </div>
        {links.length > 0 && (
          <nav
            aria-label="App"
            className="flex flex-col gap-0.5 md:[margin-top:calc(-1*var(--openui-space-2xl)+var(--openui-space-2xs))]"
          >
            {links.map((link) => (
              <AgentInterface.SidebarItem key={link.key} icon={link.icon} path={link.path}>
                {link.label}
              </AgentInterface.SidebarItem>
            ))}
          </nav>
        )}
      </div>
      <AgentInterface.SidebarContent>
        {links.length > 0 && <AgentInterface.SidebarSeparator />}
        <AgentInterface.ThreadList />
        <div className="mt-auto flex items-center gap-2 pt-1">
          <ThemeToggle className="shrink-0 border-none p-1 hover:opacity-80" />
          <Menu.Root>
            <Menu.Trigger
              className="flex min-w-0 flex-1 items-center gap-1 rounded text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
              aria-label="account menu"
            >
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate">{email}</span>
                <span className="truncate font-mono text-[10px] opacity-70">{tenant}</span>
              </span>
              <ChevronUp aria-hidden="true" className="h-3 w-3 shrink-0" />
            </Menu.Trigger>
            <Menu.Portal>
              {/* Above the sidebar's z-1000 or the popup paints under it. */}
              <Menu.Positioner
                side="top"
                align="start"
                sideOffset={6}
                className="z-[1100]"
              >
                <Menu.Popup className="min-w-48 rounded-lg border border-border bg-popover p-1.5 shadow-lg">
                  {systemRoles.includes(SYSTEM_OWNER_ROLE) && (
                    <Menu.Item className={menuItem} onClick={() => openPath("/system/settings")}>
                      <Settings2 aria-hidden="true" className="h-4 w-4" />
                      System settings
                    </Menu.Item>
                  )}
                  <Menu.Item className={menuItem} onClick={logout}>
                    <LogOut aria-hidden="true" className="h-4 w-4" />
                    Log out
                  </Menu.Item>
                </Menu.Popup>
              </Menu.Positioner>
            </Menu.Portal>
          </Menu.Root>
        </div>
      </AgentInterface.SidebarContent>
    </>
  );
}
