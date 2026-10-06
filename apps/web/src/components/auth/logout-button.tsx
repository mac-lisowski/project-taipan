"use client";

import Link from "next/link";
import type { ReactNode } from "react";

// Logout is a plain navigation to /logout: no background request to
// wait for, the cookie clears on the way out.
export function LogoutButton(): ReactNode {
  return (
    <Link
      href="/logout"
      className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
    >
      logout
    </Link>
  );
}
