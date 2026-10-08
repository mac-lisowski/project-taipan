import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";
import { UsersView } from "@/components/users/users-view";

// Owner-only registered users list; non-owners never reach this page.
export default async function UsersPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/dashboard");
  }

  return <UsersView />;
}
