// URL contract for the pane: the `pane` query param is the source of
// truth for open state on load. Values use the content codec from
// pane-state.ts, which also formats the last-used storage slot. Import
// direction stays one-way (this module -> pane-state): no cycle.

import {
  canOpenPanePath,
  initialPaneState,
  isPaneSurfacePath,
  openPane,
  paneContentOf,
  parsePaneValue,
  serializePaneContent,
  type PaneContent,
  type PaneState,
} from "@/lib/pane-state";

export const PANE_PARAM = "pane";

// State -> param value. null means "remove the param": a closed pane
// carries no `pane` value.
export function serializePaneParam(state: PaneState): string | null {
  const content = paneContentOf(state);
  return content === null ? null : serializePaneContent(content);
}

// Param value -> content. Meaningful only on chat-surface routes;
// unknown, extra-segment, and role-forbidden paths drop the param so
// the pane stays closed rather than showing an error surface.
export function parsePaneParam(
  search: string | URLSearchParams,
  pathname: string,
  systemRoles: string[],
): PaneContent | null {
  if (!isPaneSurfacePath(pathname)) return null;
  const params = typeof search === "string" ? new URLSearchParams(search) : search;
  const raw = params.get(PANE_PARAM);
  if (raw === null) return null;
  const content = parsePaneValue(raw);
  if (content === null) return null;
  if (content.kind === "view" && !canOpenPanePath(systemRoles, content.viewPath)) {
    return null;
  }
  return content;
}

// Mount-time restore: the URL decides open state and content; storage
// contributes the ratio only. persist false keeps a shared link from
// overwriting the stored last-used seed.
export function restorePaneState(
  search: string | URLSearchParams,
  pathname: string,
  systemRoles: string[],
): PaneState {
  const base = initialPaneState();
  const content = parsePaneParam(search, pathname, systemRoles);
  return content === null
    ? base
    : openPane(base, content, systemRoles, { persist: false });
}
