"use client";

import { Moon, Sun } from "lucide-react";
import type { ReactNode } from "react";
import { toggleThemeMode } from "@/lib/theme";
import { useThemeMode } from "@/lib/use-theme";

// Icon-only mode flip: shows the mode a click switches to. Used in the
// shell header and in the chat sidebar footer.
export function ThemeToggle({ className }: { className?: string }): ReactNode {
  const mode = useThemeMode();
  const Icon = mode === "dark" ? Sun : Moon;
  return (
    <button
      type="button"
      onClick={toggleThemeMode}
      aria-label={`switch to ${mode === "dark" ? "light" : "dark"} theme`}
      suppressHydrationWarning
      className={
        className ??
        "rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      }
    >
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}
