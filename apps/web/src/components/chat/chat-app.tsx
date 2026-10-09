"use client";

import {
  AgentInterface,
  type PromptTemplate,
  type Theme,
} from "@openuidev/react-ui";
import { AssistantMessage } from "@/components/chat/assistant-message";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatModelSwitcher } from "@/components/chat/chat-model-switcher";
import { QueueDispatch } from "@/components/chat/queue-dispatch";
import { LayoutDashboard, User, Users } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import {
  Brand,
  ChatSidebarContents,
  TMark,
  type ChatSidebarLink,
} from "@/components/chat/chat-sidebar";
import { AccountView } from "@/components/account/account-view";
import { useShellAccount } from "@/components/shell/shell-context";
import { OverviewView } from "@/components/dashboard/overview-view";
import { SettingsView } from "@/components/settings/settings-view";
import { UserDetailPanel } from "@/components/users/user-detail-panel";
import { UsersView } from "@/components/users/users-view";
import { chatLLM, chatStorage } from "@/lib/chat-config";
import { chatNavLinks } from "@/lib/nav";
import { useThemeMode } from "@/lib/use-theme";

// Taipan green drives the OpenUI accents; dark mode takes a lighter shade.
const brandLight: Theme = {
  interactiveAccentDefault: "oklch(0.58 0.15 155)",
  interactiveAccentHover: "oklch(0.63 0.15 155)",
  interactiveAccentPressed: "oklch(0.53 0.15 155)",
  textBrand: "oklch(0.44 0.12 155)",
  borderAccent: "oklch(0.58 0.15 155)",
};

const brandDark: Theme = {
  interactiveAccentDefault: "oklch(0.72 0.17 155)",
  interactiveAccentHover: "oklch(0.77 0.17 155)",
  interactiveAccentPressed: "oklch(0.67 0.17 155)",
  textBrand: "oklch(0.82 0.15 155)",
  borderAccent: "oklch(0.72 0.17 155)",
  // Dark green needs dark text; the SDK default assumes its blue accent.
  textAccentPrimary: "oklch(0.145 0 0)",
};

const starters = [
  {
    displayText: "Summarize",
    prompt: "Summarize the key points of our conversation so far.",
  },
  {
    displayText: "Draft an update",
    prompt: "Draft a short status update I can send to my team.",
  },
  {
    displayText: "Plan a task",
    prompt: "Help me break a large task into smaller steps.",
  },
];

// Fill-in-the-blank chip; a completion is appended to the stem, so it carries only the tail.
const promptTemplates: PromptTemplate[] = [
  {
    displayText: "Explain a page",
    prompt: "Explain how the ",
    completions: [
      { displayText: "users list", prompt: "users list works." },
      { displayText: "system settings", prompt: "system settings page works." },
      { displayText: "account page", prompt: "account page works." },
    ],
  },
];

const LINK_ICONS: Record<string, ReactNode> = {
  "/dashboard": <LayoutDashboard className="h-4 w-4" />,
  "/account": <User className="h-4 w-4" />,
  "/users": <Users className="h-4 w-4" />,
};

// Detail route for one user; built here so the users view can deep link.
function UserDetailRoute({ id, onBack }: { id: number; onBack: () => void }): ReactNode {
  return <UserDetailPanel id={id} onBack={onBack} />;
}

// App views share the chat's own scroll frame so they read as one design.
// The mobile row is the only way out of a route on small screens: the SDK
// renders no mobile header on route views.
function RouteView({
  children,
  onExit,
}: {
  children: ReactNode;
  onExit: () => void;
}): ReactNode {
  return (
    <div className="openui-agent-thread-scroll-area">
      {/* Same 880px column the SDK gives chat messages, so all views match. */}
      <div className="mx-auto flex w-full max-w-[calc(880px+2*var(--openui-space-m-l))] flex-col px-[var(--openui-space-m-l)] py-8">
        <button
          type="button"
          onClick={onExit}
          className="self-start rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:hidden"
        >
          &larr; chat
        </button>
        {children}
      </div>
    </div>
  );
}

// Keep the browser URL in step with the SDK's internal view state, so
// /dashboard, /users and /system/settings deep links land on the same surface.
function syncUrl(path: string | undefined): void {
  window.history.replaceState(null, "", path ?? "/chat");
}

// The whole authenticated app: the OpenUI chat owns the viewport, and app
// views render as SDK routes. Slot elements stay direct children of
// <AgentInterface> because slots are extracted by direct child type.
export function ChatApp({ initialPath }: { initialPath?: string }): ReactNode {
  const mode = useThemeMode();
  const account = useShellAccount();
  const [path, setPath] = useState<string | undefined>(initialPath);
  const [detailId, setDetailId] = useState<number | null>(null);
  const llm = useMemo(() => chatLLM(), []);
  const storage = useMemo(() => chatStorage(), []);
  const links: ChatSidebarLink[] = chatNavLinks(account.systemRoles).map((link) => ({
    key: link.href,
    label: link.label,
    icon: LINK_ICONS[link.href] ?? null,
    path: link.href,
  }));

  function navigate(next: string | undefined): void {
    setPath(next);
    syncUrl(next);
    // Leaving the users list drops the selected detail with it.
    if (next !== "/users") setDetailId(null);
  }

  return (
    <AgentInterface
      llm={llm}
      storage={storage}
      agentName="taipan"
      components={{ AssistantMessage }}
      starters={starters}
      theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
      path={path}
      onNavigate={navigate}
    >
      <AgentInterface.MobileHeader logo={<TMark />} agentName={<Brand />} />
      <AgentInterface.ThreadHeader>
        <ChatModelSwitcher />
      </AgentInterface.ThreadHeader>
      <AgentInterface.Welcome glowAnimation promptTemplates={promptTemplates} />
      {/* Mode C: custom composer owns the queue UI; starters are hand-rolled
          inside it because the SDK starter chip is not exported. */}
      <AgentInterface.Composer>
        <ChatComposer starters={starters} />
      </AgentInterface.Composer>
      {/* Non-slot child: stays mounted on route views so the queue keeps
          dispatching while the composer is unmounted. */}
      <QueueDispatch />
      <AgentInterface.Sidebar>
        <ChatSidebarContents
          links={links}
          email={account.email}
          tenant={account.tenant}
          systemRoles={account.systemRoles}
          openPath={navigate}
        />
      </AgentInterface.Sidebar>
      <AgentInterface.Route path="/dashboard">
        <RouteView onExit={() => navigate(undefined)}>
          <OverviewView />
        </RouteView>
      </AgentInterface.Route>
      <AgentInterface.Route path="/users">
        <RouteView onExit={() => navigate(undefined)}>
          {detailId === null ? (
            <UsersView
              onSelectUser={(id) => {
                setDetailId(id);
                // The /users URL stays: the detail is chat-internal state, not a route.
              }}
            />
          ) : (
            <UserDetailRoute
              id={detailId}
              onBack={() => {
                setDetailId(null);
                syncUrl("/users");
              }}
            />
          )}
        </RouteView>
      </AgentInterface.Route>
      <AgentInterface.Route path="/system/settings">
        <RouteView onExit={() => navigate(undefined)}>
          <SettingsView />
        </RouteView>
      </AgentInterface.Route>
      <AgentInterface.Route path="/account">
        <RouteView onExit={() => navigate(undefined)}>
          <AccountView />
        </RouteView>
      </AgentInterface.Route>
    </AgentInterface>
  );
}
