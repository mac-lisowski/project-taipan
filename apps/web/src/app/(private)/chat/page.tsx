"use client";

import { AgentInterface, openuiChatLibrary, type Theme } from "@openuidev/react-ui";
import { useRouter } from "next/navigation";
import { useMemo, type ReactNode } from "react";
import { LogoutButton } from "@/components/auth/logout-button";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { useShellAccount } from "@/components/shell/shell-context";
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

// The chat owns the whole viewport; the SDK sizes its container at
// 100dvw/100dvh, so it must never sit inside a padded scrolling shell.
export default function ChatPage(): ReactNode {
  const mode = useThemeMode();
  const router = useRouter();
  const account = useShellAccount();
  const llm = useMemo(() => chatLLM(), []);
  const storage = useMemo(() => chatStorage(), []);
  const links = chatNavLinks(account.systemRoles);

  return (
    <AgentInterface
      llm={llm}
      storage={storage}
      componentLibrary={openuiChatLibrary}
      agentName="taipan"
      starters={starters}
      theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
    >
      <AgentInterface.Sidebar>
        <div className="openui-agent-sidebar-actions">
          <AgentInterface.SidebarHeader />
          <div className="openui-agent-sidebar-primary-actions">
            <AgentInterface.NewChatButton />
          </div>
        </div>
        <AgentInterface.SidebarContent>
          {links.length > 0 && (
            <>
              <div className="flex flex-col gap-1">
                {links.map((link) => (
                  <AgentInterface.SidebarItem
                    key={link.href}
                    onClick={() => router.push(link.href)}
                  >
                    {link.label}
                  </AgentInterface.SidebarItem>
                ))}
              </div>
              <AgentInterface.SidebarSeparator />
            </>
          )}
          <AgentInterface.ThreadList />
          <div className="flex items-center gap-2 pt-1">
            <ThemeToggle className="shrink-0 border-none p-1 hover:opacity-80" />
            <span className="min-w-0 flex-1 truncate text-xs opacity-70">
              {account.email}
            </span>
            <LogoutButton />
          </div>
        </AgentInterface.SidebarContent>
      </AgentInterface.Sidebar>
    </AgentInterface>
  );
}
