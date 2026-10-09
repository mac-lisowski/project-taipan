// Shared chat surface presets: both AgentInterface instances (main and
// pane) mount with the same theme, starters, and prompt templates so the
// two chats read as one product. Values live in lib, not in chat-app, so
// the pane chat does not import a component module.

import type { PromptTemplate, Theme } from "@openuidev/react-ui";

// Taipan green drives the OpenUI accents; dark mode takes a lighter shade.
export const brandLight: Theme = {
  interactiveAccentDefault: "oklch(0.58 0.15 155)",
  interactiveAccentHover: "oklch(0.63 0.15 155)",
  interactiveAccentPressed: "oklch(0.53 0.15 155)",
  textBrand: "oklch(0.44 0.12 155)",
  borderAccent: "oklch(0.58 0.15 155)",
};

export const brandDark: Theme = {
  interactiveAccentDefault: "oklch(0.72 0.17 155)",
  interactiveAccentHover: "oklch(0.77 0.17 155)",
  interactiveAccentPressed: "oklch(0.67 0.17 155)",
  textBrand: "oklch(0.82 0.15 155)",
  borderAccent: "oklch(0.72 0.17 155)",
  // Dark green needs dark text; the SDK default assumes its blue accent.
  textAccentPrimary: "oklch(0.145 0 0)",
};

export const starters = [
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
export const promptTemplates: PromptTemplate[] = [
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
