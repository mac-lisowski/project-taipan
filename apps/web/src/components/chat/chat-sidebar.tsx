"use client";

import { AgentInterface } from "@openuidev/react-ui";
import { Menu } from "@base-ui/react/menu";
import { ChevronUp } from "lucide-react";
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

// Shell brand mark for the header slot. Passed as agentName because children
// on SidebarHeader replace the whole row and would drop the collapse button.
function Brand(): ReactNode {
  return (
    <span className="block">
      <span className="block font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        project
      </span>
      <span className="mt-1 block font-display text-2xl uppercase leading-none tracking-tight text-foreground">
        taipan
      </span>
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
    "cursor-default rounded px-2 py-1.5 text-xs text-popover-foreground data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground";

  return (
    <>
      <div className="openui-agent-sidebar-actions">
        <AgentInterface.SidebarHeader agentName={<Brand />} />
        <div className="openui-agent-sidebar-primary-actions">
          <AgentInterface.NewChatButton />
        </div>
      </div>
      <AgentInterface.SidebarContent>
        {links.length > 0 && (
          <>
            <div className="flex flex-col gap-1">
              {links.map((link) => (
                <AgentInterface.SidebarItem key={link.key} icon={link.icon} path={link.path}>
                  {link.label}
                </AgentInterface.SidebarItem>
              ))}
            </div>
            <AgentInterface.SidebarSeparator />
          </>
        )}
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
              <Menu.Positioner side="top" align="start" sideOffset={6} className="z-50">
                <Menu.Popup className="min-w-40 rounded-md border border-border bg-popover p-1 shadow-md">
                  {systemRoles.includes(SYSTEM_OWNER_ROLE) && (
                    <Menu.Item className={menuItem} onClick={() => openPath("/settings")}>
                      system settings
                    </Menu.Item>
                  )}
                  <Menu.Item className={menuItem} onClick={logout}>
                    log out
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
