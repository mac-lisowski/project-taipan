import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";
import { UsersTable } from "./users-table";

// Owner-only registered users list; non-owners never reach this page.
export default async function UsersPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/dashboard");
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <p className="font-mono text-[10px] tracking-[0.35em] text-muted-foreground">
        registered users
      </p>
      <UsersTable />
    </div>
  );
}
