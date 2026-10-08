import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";
import { UserDetailPanel } from "./user-detail";

// Owner-only account details; non-owners never reach this page.
export default async function UserDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/dashboard");
  }
  const { id } = await params;
  return <UserDetailPanel id={Number(id)} />;
}
