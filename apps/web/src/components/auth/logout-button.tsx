"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

// POST, not a Link: a GET fires on prefetch and kills the session unseen.
export function LogoutButton(): ReactNode {
  const router = useRouter();

  function onClick(): void {
    void fetch("/logout", { method: "POST" }).finally(() => {
      router.push("/");
      router.refresh();
    });
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
    >
      logout
    </button>
  );
}
