"use client";

import { AgentInterface, openuiChatLibrary, type Theme } from "@openuidev/react-ui";
import { LayoutDashboard, Settings2, Users } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { ChatSidebar, type ChatSidebarLink } from "@/components/chat/chat-sidebar";
import { useShellAccount } from "@/components/shell/shell-context";
import { OverviewView } from "@/components/dashboard/overview-view";
import { SettingsView } from "@/components/settings/settings-view";
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

const LINK_ICONS: Record<string, ReactNode> = {
  "/dashboard": <LayoutDashboard className="h-4 w-4" />,
  "/users": <Users className="h-4 w-4" />,
  "/settings": <Settings2 className="h-4 w-4" />,
};

// The chat owns the whole viewport; app views render as SDK routes so the
// sidebar, threads, and branding never disappear between views.
export default function ChatPage(): ReactNode {
  const mode = useThemeMode();
  const account = useShellAccount();
  const [path, setPath] = useState<string | undefined>(undefined);
  const llm = useMemo(() => chatLLM(), []);
  const storage = useMemo(() => chatStorage(), []);
  const links: ChatSidebarLink[] = chatNavLinks(account.systemRoles).map((link) => ({
    key: link.href,
    label: link.label,
    icon: LINK_ICONS[link.href] ?? null,
    path: link.href,
  }));

  return (
    <AgentInterface
      llm={llm}
      storage={storage}
      componentLibrary={openuiChatLibrary}
      agentName="taipan"
      starters={starters}
      theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
      path={path}
      onNavigate={setPath}
    >
      <ChatSidebar
        links={links}
        email={account.email}
        tenant={account.tenant}
        systemRoles={account.systemRoles}
        openPath={setPath}
      />
      <AgentInterface.Route path="/dashboard">
        <OverviewView />
      </AgentInterface.Route>
      <AgentInterface.Route path="/users">
        <UsersView />
      </AgentInterface.Route>
      <AgentInterface.Route path="/settings">
        <SettingsView />
      </AgentInterface.Route>
    </AgentInterface>
  );
}
