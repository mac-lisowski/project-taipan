// The one system role the API grants today; keep in step with the backend enum.
export const SYSTEM_OWNER_ROLE = "system_owner";

// User detail has no real route (/users?user=N only), so the pane
// router owns a bare path for it. Defined here next to the owner gate
// so pane-state can share the one spelling.
export const PANE_USER_DETAIL_PATH = "/users/detail";

// Paths gated to system_owner. The sidebar nav, the account menu, the
// private nav list, and the pane router all consume this one check.
const OWNER_ONLY_PATHS: readonly string[] = [
  "/users",
  "/system/settings",
  PANE_USER_DETAIL_PATH,
];

export function isOwnerOnlyPath(path: string): boolean {
  return OWNER_ONLY_PATHS.includes(path);
}

// The gate every nav source shares: a path is reachable unless it is
// owner-only and the account lacks the role.
export function canSeeNavPath(systemRoles: string[], path: string): boolean {
  return !isOwnerOnlyPath(path) || systemRoles.includes(SYSTEM_OWNER_ROLE);
}

export type NavItem = {
  href: string;
  label: string;
  icon?: "gear" | "users";
};

export type NavSection = {
  heading: string | null;
  items: NavItem[];
};

// Full-viewport ChatApp paths: the private shell hands these to the chat
// surface instead of wrapping them in its own sidebar chrome. /chat plus
// every AgentInterface.Route path registered in chat-app.tsx.
export const CHAT_SURFACE_ROUTES: readonly string[] = [
  "/chat",
  "/dashboard",
  "/users",
  "/system/settings",
  "/account",
];

// Sidebar sections for non-chat private routes. The chat surface carries no
// shell nav of its own; the system section exists only for system_owner.
export function privateNav(systemRoles: string[]): NavSection[] {
  const items = (
    [
      { href: "/users", label: "users", icon: "users" },
      { href: "/system/settings", label: "settings", icon: "gear" },
    ] satisfies NavItem[]
  ).filter((item) => canSeeNavPath(systemRoles, item.href));
  return items.length === 0 ? [] : [{ heading: "system", items }];
}

// Links composed into the OpenUI chat sidebar above the thread list.
// Overview is the member landing view; users is owner-only. System
// settings lives in the account dropdown, not here.
export function chatNavLinks(systemRoles: string[]): NavItem[] {
  return (
    [
      { href: "/dashboard", label: "Overview" },
      { href: "/account", label: "Account", icon: "gear" },
      { href: "/users", label: "Users", icon: "users" },
    ] satisfies NavItem[]
  ).filter((link) => canSeeNavPath(systemRoles, link.href));
}
