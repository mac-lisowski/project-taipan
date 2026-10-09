"use client";

import type { ReactNode } from "react";
// Route folder owns the table for now; chat surface will rehome it later.
import { UsersTable } from "@/app/(private)/users/users-table";
import type { UsersBoot } from "@/lib/users-list";

// Full users screen body; the server page adds the owner gate and the
// one-page fetch this view renders.
export function UsersView({
  boot,
  onSelectUser,
}: {
  boot: UsersBoot;
  onSelectUser?: (id: number) => void;
}): ReactNode {
  return (
    <div className="flex w-full flex-col gap-4">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        Registered users
      </p>
      <UsersTable boot={boot} onSelectUser={onSelectUser} />
    </div>
  );
}
