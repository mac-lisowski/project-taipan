// App-owned surface navigation contract. Views call one `navigate`
// instead of next/navigation so the same call site runs on the main
// surface (real navigation) and inside a pane (pane-state writes).
// Pure module: no React or DOM imports so the pane translation is
// unit-testable.

import { PANE_USER_DETAIL_PATH } from "@/lib/nav";
import {
  canOpenPanePath,
  navigatePaneView,
  selectPaneDetail,
  supportsPaneDetail,
  type PaneState,
} from "@/lib/pane-state";

export type ShellNavTarget = {
  /** App surface path; may carry query params ("/users?user=3"). */
  path: string;
  /** undefined lets the path's `user` param win; null clears. */
  detailId?: number | null;
  /** In-place list writes (filters, detail picks): no new entry. */
  replace?: boolean;
};

export type ShellNavigate = (target: ShellNavTarget) => void;

// Splits a nav target into its route path and the embedded user detail
// id, with the same validity rules as parseUsersFilters.
export function splitTargetPath(path: string): {
  pathname: string;
  user: number | null;
} {
  const q = path.indexOf("?");
  const pathname = q === -1 ? path : path.slice(0, q);
  const raw = q === -1 ? null : new URLSearchParams(path.slice(q)).get("user");
  const parsed = raw === null ? Number.NaN : Number.parseInt(raw, 10);
  return {
    pathname,
    user: Number.isInteger(parsed) && parsed >= 1 ? parsed : null,
  };
}

// Pane half of the contract: a picked record lands on the pane's own
// detail path; `replace` is ignored because the pane writes pane state,
// not browser history.
export function paneNavWrite(
  state: PaneState,
  target: ShellNavTarget,
  systemRoles: string[] = [],
): PaneState {
  const { pathname, user } = splitTargetPath(target.path);
  const detail = target.detailId === undefined ? user : target.detailId;
  const viewPath =
    detail !== null && pathname === "/users" ? PANE_USER_DETAIL_PATH : pathname;
  if (!canOpenPanePath(systemRoles, viewPath)) return state;
  if (viewPath === state.viewPath) {
    if (!supportsPaneDetail(viewPath) || state.detailId === detail) return state;
    return selectPaneDetail(state, detail);
  }
  return navigatePaneView(state, viewPath, systemRoles, detail);
}

// Binds the pane write to a host-owned state setter; PaneNavProvider
// wraps this in context, tests drive it directly.
export function paneNavigate(
  state: PaneState,
  systemRoles: string[],
  dispatch: (next: PaneState) => void,
): ShellNavigate {
  return (target) => {
    // Refused and no-op writes must not churn the host state.
    const next = paneNavWrite(state, target, systemRoles);
    if (next !== state) dispatch(next);
  };
}
