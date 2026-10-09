"use client";

// The second, independent chat surface: a nested AgentInterface inside
// the pane. Every per-instance store is built here (queue, model, LLM
// binding, unseeded storage) so nothing reaches the main chat's
// singletons. The SDK's context is per instance, so useThread hooks in
// the shared composer and queue components bind to this instance.

import { AgentInterface } from "@openuidev/react-ui";
import { useMemo, type ReactNode } from "react";

import { AssistantMessage } from "@/components/chat/assistant-message";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatModelSwitcher } from "@/components/chat/chat-model-switcher";
import { Brand, TMark } from "@/components/chat/chat-sidebar";
import { QueueDispatch } from "@/components/chat/queue-dispatch";
import { chatLLM, chatStorage } from "@/lib/chat-config";
import { createChatModelStore } from "@/lib/chat-model";
import { ChatModelProvider } from "@/lib/chat-model-context";
import {
  brandDark,
  brandLight,
  promptTemplates,
  starters,
} from "@/lib/chat-presets";
import { createChatQueueStore } from "@/lib/chat-queue";
import { ChatQueueProvider } from "@/lib/chat-queue-context";
import { useThemeMode } from "@/lib/use-theme";

export function PaneChat(): ReactNode {
  const mode = useThemeMode();
  // No storage key on the model store: the pane pick must not persist
  // into the shared taipan-chat-model slot the main chat reads.
  const modelStore = useMemo(() => createChatModelStore(), []);
  const queueStore = useMemo(() => createChatQueueStore(), []);
  const llm = useMemo(() => chatLLM(modelStore), [modelStore]);
  // chatStorage(null): the shell's seeded adapter is single-consumer;
  // this instance fetches its thread list on mount.
  const storage = useMemo(() => chatStorage(null), []);

  return (
    <ChatQueueProvider store={queueStore}>
      <ChatModelProvider store={modelStore}>
        <AgentInterface
          llm={llm}
          storage={storage}
          agentName="taipan"
          components={{ AssistantMessage }}
          starters={starters}
          theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
          artifactAutoOpen={false}
        >
          <AgentInterface.MobileHeader
            logo={<TMark />}
            agentName={<Brand />}
          />
          <AgentInterface.ThreadHeader>
            <ChatModelSwitcher />
          </AgentInterface.ThreadHeader>
          <AgentInterface.Welcome
            glowAnimation
            promptTemplates={promptTemplates}
          />
          <AgentInterface.Composer>
            <ChatComposer starters={starters} />
          </AgentInterface.Composer>
          {/* Rest-slot child: keeps dispatching when the pane remounts
              nothing else on kind switches. No Sidebar slot: the SDK
              default sidebar is the thread picker this chat wants. */}
          <QueueDispatch />
        </AgentInterface>
      </ChatModelProvider>
    </ChatQueueProvider>
  );
}
