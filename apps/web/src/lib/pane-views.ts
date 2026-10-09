// Pane view router: the pane's internal viewPath maps to a view id the
// pane body renders. Unknown paths resolve to null so the pane drops
// content instead of showing an error surface (pane-state already
// refuses them, this is the second wall).

import { PANE_USER_DETAIL_PATH } from "@/lib/nav";
import { isPaneViewPath, type PaneState } from "@/lib/pane-state";

export type PaneViewId =
  | "overview"
  | "users"
  | "user-detail"
  | "settings"
  | "account";

export type PaneViewMeta = { id: PaneViewId; title: string };

export const PANE_VIEW_TABLE: Readonly<Record<string, PaneViewMeta>> = {
  "/dashboard": { id: "overview", title: "overview" },
  "/users": { id: "users", title: "users" },
  [PANE_USER_DETAIL_PATH]: { id: "user-detail", title: "user detail" },
  "/system/settings": { id: "settings", title: "system settings" },
  "/account": { id: "account", title: "account" },
};

export function paneViewFor(viewPath: string | null): PaneViewMeta | null {
  if (viewPath === null || !isPaneViewPath(viewPath)) return null;
  return PANE_VIEW_TABLE[viewPath] ?? null;
}

// Header title for the current pane content; the shell owns the chrome,
// this only names it.
export function paneTitle(state: PaneState): string {
  if (state.kind === "chat") return "chat";
  return paneViewFor(state.viewPath)?.title ?? "pane";
}
