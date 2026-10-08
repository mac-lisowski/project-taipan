"use client";

import type { ReactNode } from "react";
// Route folder owns the table for now; chat surface will rehome it later.
import { UsersTable } from "@/app/(private)/users/users-table";

// Full users screen body; the server page adds the owner gate around it.
export function UsersView(): ReactNode {
  return (
    <div className="flex w-full flex-col gap-4">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        registered users
      </p>
      <UsersTable />
    </div>
  );
}
