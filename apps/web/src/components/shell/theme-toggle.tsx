"use client";

import type { ReactNode } from "react";
import { toggleThemeMode } from "@/lib/theme";
import { useThemeMode } from "@/lib/use-theme";

// Header control beside the menu toggle; the label names the mode a
// click switches to, matching the show/hide menu wording.
export function ThemeToggle(): ReactNode {
  const mode = useThemeMode();
  return (
    <button
      type="button"
      onClick={toggleThemeMode}
      suppressHydrationWarning
      className="border border-border px-2 py-1 font-mono text-[11px] text-muted-foreground transition-colors hover:text-foreground"
    >
      {mode === "dark" ? "light mode" : "dark mode"}
    </button>
  );
}
