import type { ReactNode } from "react";
import { ChatApp } from "@/components/chat/chat-app";

// Every private surface is the chat app; the URL only picks the view.
export default function DashboardPage(): ReactNode {
  return <ChatApp initialPath="/dashboard" />;
}
