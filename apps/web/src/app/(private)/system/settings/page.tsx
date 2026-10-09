import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { ChatApp } from "@/components/chat/chat-app";
import { SYSTEM_OWNER_ROLE } from "@/lib/nav";
import { requireAccount } from "@/lib/session";

// Owner-only gate stays server-side; non-owners land back in the chat.
export default async function SettingsPage(): Promise<ReactNode> {
  const me = await requireAccount();
  if (!me.system_roles.includes(SYSTEM_OWNER_ROLE)) {
    redirect("/chat");
  }

  return <ChatApp initialPath="/system/settings" />;
}
