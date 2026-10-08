import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ChatApp } from "@/components/chat/chat-app";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";

// Owner-only registered users list; non-owners never reach this page.
export default async function UsersPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/chat");
  }

  return <ChatApp initialPath="/users" />;
}
