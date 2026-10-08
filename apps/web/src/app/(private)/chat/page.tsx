import type { ReactNode } from "react";
import { ChatApp } from "@/components/chat/chat-app";

// The chat is the app; every other private view renders inside it.
export default function ChatPage(): ReactNode {
  return <ChatApp />;
}
