"use client";

// The pane body: kind switch plus scroll frame. The pane chat mounts
// lazily on first chat-kind open and then stays mounted hidden, so a
// running reply survives a switch to a view and back. View content runs
// under the pane nav provider so view-internal moves (overview link,
// detail panel back) write pane state, never the real router.

import { useState, type ReactNode } from "react";

import { AccountView } from "@/components/account/account-view";
import { PaneChat } from "@/components/chat/pane-chat";
import { PaneUsersView } from "@/components/chat/pane-users-view";
import { OverviewView } from "@/components/dashboard/overview-view";
import { SettingsView } from "@/components/settings/settings-view";
import { useShellAccount } from "@/components/shell/shell-context";
import { usePaneStore } from "@/lib/pane-state-context";
import { paneViewFor } from "@/lib/pane-views";
import { PaneNavProvider } from "@/lib/shell-nav-context";

function PaneViewContent({
  viewPath,
  detailId,
}: {
  viewPath: string;
  detailId: number | null;
}): ReactNode {
  const view = paneViewFor(viewPath);
  if (view === null) return null;
  // Same component slot for list and detail keeps the adapter's filter
  // state alive across the detail round trip.
  switch (view.id) {
    case "overview":
      return <OverviewView />;
    case "users":
      return <PaneUsersView detailId={null} />;
    case "user-detail":
      return <PaneUsersView detailId={detailId} />;
    case "settings":
      return <SettingsView />;
    case "account":
      return <AccountView />;
  }
}

export function PaneBody(): ReactNode {
  const { state, dispatch } = usePaneStore();
  const account = useShellAccount();
  const [chatMounted, setChatMounted] = useState(state.kind === "chat");
  // Sticky flag; render-phase set is the documented pattern.
  if (state.kind === "chat" && !chatMounted) setChatMounted(true);

  return (
    <>
      {chatMounted && (
        <div className="taipan-pane__chat" hidden={state.kind !== "chat"}>
          <PaneChat />
        </div>
      )}
      {state.kind === "view" && state.viewPath !== null && (
        <PaneNavProvider
          state={state}
          systemRoles={account.systemRoles}
          dispatch={dispatch}
        >
          <div className="taipan-pane__view">
            <PaneViewContent
              viewPath={state.viewPath}
              detailId={state.detailId}
            />
          </div>
        </PaneNavProvider>
      )}
    </>
  );
}
