// Pure model for the split-screen pane: open flag, content kind,
// pane-internal view path, optional detail selection, split ratio, and
// the in-pane back stack. localStorage keeps only the ratio and the
// last-used content (a stored open flag would race the URL); the
// `pane` query param contract lives in pane-url.ts. No DOM or React
// imports; storage access is guarded so the module runs without a
// window.

import { CHAT_SURFACE_ROUTES, SYSTEM_OWNER_ROLE } from "@/lib/nav";

export type PaneContentKind = "chat" | "view";

export type PaneContent = { kind: "chat" } | { kind: "view"; viewPath: string };

// One pane location: a view path plus an optional detail selection
// (today the open user-detail record). Detail ids live here only;
// they never serialize into the URL.
export type PaneLocation = { viewPath: string; detailId: number | null };

export type PaneState = {
  open: boolean;
  kind: PaneContentKind;
  viewPath: string | null;
  detailId: number | null;
  // The user's picked ratio. Clamps apply at layout time only, so a
  // narrow screen never destroys the stored pick.
  ratio: number;
  // In-pane view history; resets on kind switch, content replace,
  // and close.
  backStack: PaneLocation[];
};

export type PaneAction =
  | "open"
  | "close"
  | "navigateView"
  | "selectDetail"
  | "back"
  | "setRatio";

export const DEFAULT_PANE_RATIO = 0.5;

// Width floors per spec "Divider and layout": thread region and pane
// keep ~360px each after the fixed ~272px shell sidebar.
export const PANE_MIN_WIDTH = 360;
export const THREAD_MIN_WIDTH = 360;
export const SHELL_SIDEBAR_WIDTH = 272;

// User detail has no real route (/users?user=N only), so the pane gets
// its own bare path for the router table.
export const PANE_USER_DETAIL_PATH = "/users/detail";

// Chat-surface routes minus /chat (that content is the chat kind) plus
// the detail view. Unknown or extra-segment paths drop the param.
export const PANE_VIEW_PATHS: readonly string[] = [
  ...CHAT_SURFACE_ROUTES.filter((path) => path !== "/chat"),
  PANE_USER_DETAIL_PATH,
];

// The single owner-path set the sidebar nav, account menu, private nav
// list, and pane router consume; user detail inherits the /users gate.
const OWNER_ONLY_PATHS: readonly string[] = [
  "/users",
  "/system/settings",
  PANE_USER_DETAIL_PATH,
];

// Pure owner gate on a path alone; nav sources consume this while
// canOpenPanePath composes it with pane membership.
export function isOwnerOnlyPath(path: string): boolean {
  return OWNER_ONLY_PATHS.includes(path);
}

const RATIO_KEY = "taipan-pane-ratio";
const LAST_CONTENT_KEY = "taipan-pane-last";

const DEFAULT_CONTENT: PaneContent = { kind: "chat" };

// Which actions are legal per state. Transitions refuse illegal moves
// by returning the input unchanged; callers gate affordances on this.
const LEGALITY: Record<PaneAction, (state: PaneState) => boolean> = {
  // Always legal: opening while open replaces the content.
  open: () => true,
  close: (state) => state.open,
  navigateView: (state) =>
    state.open && state.kind === "view" && state.viewPath !== null,
  // Same live-view requirement plus a detail-capable current path.
  selectDetail: (state) =>
    state.open &&
    state.kind === "view" &&
    state.viewPath !== null &&
    supportsPaneDetail(state.viewPath),
  back: (state) => state.open && state.kind === "view" && state.backStack.length > 0,
  // The ratio is a surface preference; it applies even while closed.
  setRatio: () => true,
};

export function paneAllows(state: PaneState, action: PaneAction): boolean {
  return LEGALITY[action](state);
}

export function isPaneSurfacePath(pathname: string): boolean {
  return CHAT_SURFACE_ROUTES.includes(pathname);
}

export function isPaneViewPath(path: string): boolean {
  return PANE_VIEW_PATHS.includes(path);
}

export function supportsPaneDetail(path: string): boolean {
  return path === PANE_USER_DETAIL_PATH;
}

// The one role gate: unknown pane paths refuse for everyone, and
// owner-only paths need system_owner from the same systemRoles list
// the shell account carries.
export function canOpenPanePath(systemRoles: string[], path: string): boolean {
  if (!isPaneViewPath(path)) return false;
  if (!isOwnerOnlyPath(path)) return true;
  return systemRoles.includes(SYSTEM_OWNER_ROLE);
}

function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // SSR or blocked storage: read as empty.
  }
}

function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage blocked: the in-session state still applies.
  }
}

export function readPaneRatio(): number {
  const raw = readStored(RATIO_KEY);
  const parsed = raw === null ? Number.NaN : Number.parseFloat(raw);
  if (!Number.isFinite(parsed)) return DEFAULT_PANE_RATIO;
  return Math.min(Math.max(parsed, 0), 1);
}

export function readLastPaneContent(): PaneContent | null {
  const raw = readStored(LAST_CONTENT_KEY);
  return raw === null ? null : parsePaneValue(raw);
}

export function initialPaneState(): PaneState {
  return {
    open: false,
    kind: "chat",
    viewPath: null,
    detailId: null,
    ratio: readPaneRatio(),
    backStack: [],
  };
}

export function paneContentOf(state: PaneState): PaneContent | null {
  if (!state.open) return null;
  if (state.kind === "chat") return { kind: "chat" };
  return state.viewPath === null ? null : { kind: "view", viewPath: state.viewPath };
}

// persist false is the URL-restore path: a shared link must not
// overwrite the stored last-used seed.
export function openPane(
  state: PaneState,
  target: PaneContent | null,
  systemRoles: string[] = [],
  options: { persist?: boolean } = {},
): PaneState {
  let content = target ?? readLastPaneContent() ?? DEFAULT_CONTENT;
  if (content.kind === "view" && !canOpenPanePath(systemRoles, content.viewPath)) {
    if (target !== null) return state;
    content = DEFAULT_CONTENT; // stale or role-lost seed falls back
  }
  const serialized = serializePaneContent(content);
  if (options.persist !== false && serialized !== null) {
    writeStored(LAST_CONTENT_KEY, serialized);
  }
  return {
    open: true,
    kind: content.kind,
    viewPath: content.kind === "view" ? content.viewPath : null,
    detailId: null,
    ratio: state.ratio,
    backStack: [],
  };
}

export function closePane(state: PaneState): PaneState {
  if (!state.open) return state;
  return { open: false, kind: "chat", viewPath: null, detailId: null, ratio: state.ratio, backStack: [] };
}

// In-pane view navigation; pushes the current location onto the back
// stack. Never touches the real router.
export function navigatePaneView(
  state: PaneState,
  viewPath: string,
  systemRoles: string[] = [],
  detailId: number | null = null,
): PaneState {
  const content = paneContentOf(state);
  if (!paneAllows(state, "navigateView") || content?.kind !== "view") return state;
  if (!canOpenPanePath(systemRoles, viewPath)) return state;
  const detail = supportsPaneDetail(viewPath) ? detailId : null;
  if (content.viewPath === viewPath && state.detailId === detail) return state;
  const current: PaneLocation = { viewPath: content.viewPath, detailId: state.detailId };
  return { ...state, viewPath, detailId: detail, backStack: [...state.backStack, current] };
}

// Changes the detail selection inside a detail-capable view; a
// location change, so it pushes the back stack.
export function selectPaneDetail(state: PaneState, detailId: number | null): PaneState {
  if (!paneAllows(state, "selectDetail") || state.viewPath === null) return state;
  if (state.detailId === detailId) return state;
  const current: PaneLocation = { viewPath: state.viewPath, detailId: state.detailId };
  return { ...state, detailId, backStack: [...state.backStack, current] };
}

export function paneBack(state: PaneState): PaneState {
  if (!paneAllows(state, "back")) return state;
  const backStack = state.backStack.slice();
  const prev = backStack.pop();
  if (prev === undefined) return state;
  return { ...state, viewPath: prev.viewPath, detailId: prev.detailId, backStack };
}

export function setPaneRatio(state: PaneState, ratio: number): PaneState {
  if (!Number.isFinite(ratio)) return state;
  const next = Math.min(Math.max(ratio, 0), 1);
  if (next === state.ratio) return state;
  writeStored(RATIO_KEY, String(next));
  return { ...state, ratio: next };
}

// Layout-time clamp: keeps the pane and the thread region at or above
// their pixel floors for the given container width. Pure math; the
// stored ratio stays untouched.
export function clampPaneRatio(ratio: number, containerWidth: number): number {
  if (!Number.isFinite(ratio)) return DEFAULT_PANE_RATIO;
  if (!Number.isFinite(containerWidth) || containerWidth <= 0) return ratio;
  const maxPane = containerWidth - SHELL_SIDEBAR_WIDTH - THREAD_MIN_WIDTH;
  // Floors conflict below ~992px of container: the pane floor wins,
  // and the overlay take-over below ~1024px keeps this band tiny.
  const high = Math.max(PANE_MIN_WIDTH, maxPane);
  const panePx = Math.min(Math.max(ratio * containerWidth, PANE_MIN_WIDTH), high);
  return panePx / containerWidth;
}

// Codec shared by the `pane` param (pane-url.ts) and the last-used
// slot: detail degrades to its list so a stale id never reopens.
export function serializePaneContent(content: PaneContent): string | null {
  if (content.kind === "chat") return "chat";
  if (!isPaneViewPath(content.viewPath)) return null;
  const viewPath =
    content.viewPath === PANE_USER_DETAIL_PATH ? "/users" : content.viewPath;
  return `view:${viewPath}`;
}

export function parsePaneValue(raw: string): PaneContent | null {
  if (raw === "chat") return { kind: "chat" };
  if (!raw.startsWith("view:")) return null;
  const viewPath = raw.slice("view:".length);
  if (!isPaneViewPath(viewPath)) return null;
  return {
    kind: "view",
    viewPath: viewPath === PANE_USER_DETAIL_PATH ? "/users" : viewPath,
  };
}
