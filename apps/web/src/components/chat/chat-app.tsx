"use client";

import { AgentInterface } from "@openuidev/react-ui";
import { AssistantMessage } from "@/components/chat/assistant-message";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatModelSwitcher } from "@/components/chat/chat-model-switcher";
import { QueueDispatch } from "@/components/chat/queue-dispatch";
import { RouteView } from "@/components/chat/route-view";
import { LayoutDashboard, PanelRight, User, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState, type ReactNode } from "react";
import {
  Brand,
  ChatSidebarContents,
  TMark,
  type ChatSidebarLink,
} from "@/components/chat/chat-sidebar";
import { ThreadShareControls } from "@/components/chat/thread-share-controls";
import { AccountView } from "@/components/account/account-view";
import { useShellAccount, useShellThreads } from "@/components/shell/shell-context";
import { OverviewView } from "@/components/dashboard/overview-view";
import { SettingsView } from "@/components/settings/settings-view";
import { UserDetailPanel } from "@/components/users/user-detail-panel";
import { UsersView } from "@/components/users/users-view";
import { SplitPane } from "@/components/chat/split-pane";
import { chatLLM, chatStorage } from "@/lib/chat-config";
import { chatModelStore } from "@/lib/chat-model";
import {
  brandDark,
  brandLight,
  promptTemplates,
  starters,
} from "@/lib/chat-presets";
import { ChatModelProvider } from "@/lib/chat-model-context";
import { chatQueue } from "@/lib/chat-queue";
import { ChatQueueProvider } from "@/lib/chat-queue-context";
import { chatNavLinks } from "@/lib/nav";
import { PaneStateProvider, usePaneActions } from "@/lib/pane-state-context";
import { appendPaneParam, carryPaneQuery } from "@/lib/pane-url";
import { splitTargetPath, type ShellNavigate } from "@/lib/shell-nav";
import { ShellNavProvider } from "@/lib/shell-nav-context";
import { usersPath, type UsersBoot } from "@/lib/users-list";
import type { SwitchRead } from "@/lib/system-settings";
import { useThemeMode } from "@/lib/use-theme";

const LINK_ICONS: Record<string, ReactNode> = {
  "/dashboard": <LayoutDashboard className="h-4 w-4" />,
  "/account": <User className="h-4 w-4" />,
  "/users": <Users className="h-4 w-4" />,
};

// The URL stays in step with the SDK view; same-path writes keep the
// whole query, cross-path writes keep only `pane` (page params stay on
// their own path).
function syncUrl(path: string | undefined): void {
  const target = path ?? "/chat";
  const query = carryPaneQuery(
    target,
    window.location.pathname,
    window.location.search,
  );
  window.history.replaceState(null, "", target + query);
}

// Thread-header affordance: opens the second chat in the pane. Hidden
// under 1024px like every open-in-pane affordance.
function SplitChatButton(): ReactNode {
  const { open } = usePaneActions();
  return (
    <button
      type="button"
      aria-label="open a second chat in the pane"
      title="Split: second chat"
      onClick={() => open({ kind: "chat" })}
      className="hidden rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground lg:inline-flex"
    >
      <PanelRight className="h-4 w-4" />
    </button>
  );
}

// The whole authenticated app: the OpenUI chat owns the viewport, and app
// views render as SDK routes. Slot elements stay direct children of
// <AgentInterface> because slots are extracted by direct child type.
export function ChatApp({
  initialPath,
  usersBoot,
  settingsBoot,
}: {
  initialPath?: string;
  usersBoot?: UsersBoot;
  settingsBoot?: SwitchRead;
}): ReactNode {
  const mode = useThemeMode();
  const account = useShellAccount();
  const router = useRouter();
  const [path, setPath] = useState<string | undefined>(initialPath);
  // The users detail is the `user` URL param, so it deep links and shares.
  const detailId = usersBoot?.filters.user ?? null;
  const llm = useMemo(() => chatLLM(chatModelStore), []);
  // The shell owns the seeded storage; pages without it get an unseeded one.
  const shellStorage = useShellThreads();
  const fallbackStorage = useMemo(() => chatStorage(null), []);
  const storage = shellStorage ?? fallbackStorage;
  const links: ChatSidebarLink[] = chatNavLinks(account.systemRoles).map((link) => ({
    key: link.href,
    label: link.label,
    icon: LINK_ICONS[link.href] ?? null,
    path: link.href,
  }));

  const navigate = useCallback((next: string | undefined): void => {
    setPath(next);
    syncUrl(next);
  }, []);

  // The one surface-nav entry the shell hook resolves to. /users is
  // server-rendered so it takes a real navigation; other route views
  // switch in place (a push would remount the chat and kill streams).
  const surfaceNav = useCallback<ShellNavigate>(
    (target) => {
      const { pathname } = splitTargetPath(target.path);
      if (target.replace === true) {
        // List writes only ever target /users; replace keeps history clean.
        router.replace(appendPaneParam(target.path, window.location.search), {
          scroll: false,
        });
        return;
      }
      if (pathname === "/users") {
        // The SDK view moves at once; the push brings a fresh server render.
        setPath("/users");
        // A named detail id folds into the `user` param the list reads.
        const url =
          typeof target.detailId === "number" && !target.path.includes("?")
            ? `${target.path}?user=${target.detailId}`
            : target.path;
        router.push(appendPaneParam(url, window.location.search));
        return;
      }
      // SDK routes match the bare path; a stray query would blank the view.
      navigate(pathname);
    },
    [router, navigate],
  );

  // SDK nav entries (sidebar items, onNavigate) reuse the same contract.
  function openSurfaceLink(next: string | undefined): void {
    if (next === undefined) navigate(undefined);
    else surfaceNav({ path: next });
  }

  const shareControls = <ThreadShareControls />;

  return (
    <ShellNavProvider navigate={surfaceNav}>
      {/* Explicit stores so a future pane mounts the same providers with
          its own instances; pane state wraps both sides' entry points. */}
      <PaneStateProvider systemRoles={account.systemRoles}>
        <ChatQueueProvider store={chatQueue}>
          <ChatModelProvider store={chatModelStore}>
            <AgentInterface
              llm={llm}
              storage={storage}
              agentName="taipan"
              components={{ AssistantMessage }}
              starters={starters}
              theme={{ mode, lightTheme: brandLight, darkTheme: brandDark }}
              path={path}
              onNavigate={openSurfaceLink}
              // No artifact renderer may claim the detailed-view slot.
              artifactAutoOpen={false}
            >
              <AgentInterface.MobileHeader
                logo={<TMark />}
                agentName={<Brand />}
                actions={shareControls}
              />
              <AgentInterface.ThreadHeader>
                <ChatModelSwitcher />
                {shareControls}
                <SplitChatButton />
              </AgentInterface.ThreadHeader>
              <AgentInterface.Welcome glowAnimation promptTemplates={promptTemplates} />
              {/* Mode C: custom composer owns the queue UI; starters are hand-rolled
                  inside it because the SDK starter chip is not exported. */}
              <AgentInterface.Composer>
                <ChatComposer starters={starters} />
              </AgentInterface.Composer>
              {/* Non-slot child: stays mounted on route views so the queue keeps
                  dispatching while the composer is unmounted. */}
              <QueueDispatch />
              {/* Non-slot child: the split pane docks right of the thread region. */}
              <SplitPane />
              <AgentInterface.Sidebar>
                <ChatSidebarContents
                  links={links}
                  email={account.email}
                  tenant={account.tenant}
                  systemRoles={account.systemRoles}
                  openPath={openSurfaceLink}
                />
              </AgentInterface.Sidebar>
              <AgentInterface.Route path="/dashboard">
                <RouteView onExit={() => navigate(undefined)}>
                  <OverviewView />
                </RouteView>
              </AgentInterface.Route>
              <AgentInterface.Route path="/users">
                <RouteView onExit={() => navigate(undefined)}>
                  {usersBoot === undefined ? null : detailId === null ? (
                    <UsersView
                      boot={usersBoot}
                      onSelectUser={(id) => {
                        // Row selection keeps filters and page in the URL.
                        surfaceNav({
                          path: usersPath({ ...usersBoot.filters, user: id }),
                          detailId: id,
                          replace: true,
                        });
                      }}
                    />
                  ) : (
                    <UserDetailPanel
                      id={detailId}
                      onBack={() =>
                        surfaceNav({
                          path: usersPath({ ...usersBoot.filters, user: null }),
                          detailId: null,
                          replace: true,
                        })
                      }
                    />
                  )}
                </RouteView>
              </AgentInterface.Route>
              <AgentInterface.Route path="/system/settings">
                <RouteView onExit={() => navigate(undefined)}>
                  <SettingsView initial={settingsBoot} />
                </RouteView>
              </AgentInterface.Route>
              <AgentInterface.Route path="/account">
                <RouteView onExit={() => navigate(undefined)}>
                  <AccountView />
                </RouteView>
              </AgentInterface.Route>
            </AgentInterface>
          </ChatModelProvider>
        </ChatQueueProvider>
      </PaneStateProvider>
    </ShellNavProvider>
  );
}
