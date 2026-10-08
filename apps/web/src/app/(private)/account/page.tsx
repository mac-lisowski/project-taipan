import type { ReactNode } from "react";
import { ChatApp } from "@/components/chat/chat-app";

// Account is a view inside the chat app; the URL deep link lands on it.
export default function AccountPage(): ReactNode {
  return <ChatApp initialPath="/account" />;
}
