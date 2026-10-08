"use client";

import {
  AgentInterface,
  openuiChatLibrary,
  type Theme,
} from "@openuidev/react-ui";
import { useMemo } from "react";
import { chatLLM, chatStorage } from "@/lib/chat-config";
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

// The OpenUI chat canvas: adapters point at the BFF, mode follows the app.
export default function ChatPage() {
  const mode = useThemeMode();
  const llm = useMemo(() => chatLLM(), []);
  const storage = useMemo(() => chatStorage(), []);
  return (
    <div className="h-[calc(100dvh-8rem)] min-h-[480px]">
      <AgentInterface
        llm={llm}
        storage={storage}
        componentLibrary={openuiChatLibrary}
        agentName="taipan"
        starters={starters}
        theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
      />
    </div>
  );
}
