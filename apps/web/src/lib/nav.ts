// The one system role the API grants today; keep in step with the backend enum.
export const SYSTEM_OWNER_ROLE = "system_owner";

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
  const sections: NavSection[] = [];
  if (systemRoles.includes(SYSTEM_OWNER_ROLE)) {
    sections.push({
      heading: "system",
      items: [
        { href: "/users", label: "users", icon: "users" },
        { href: "/system/settings", label: "settings", icon: "gear" },
      ],
    });
  }
  return sections;
}

// Links composed into the OpenUI chat sidebar above the thread list.
// Overview is the member landing view; users is owner-only. System
// settings lives in the account dropdown, not here.
export function chatNavLinks(systemRoles: string[]): NavItem[] {
  const links: NavItem[] = [
    { href: "/dashboard", label: "Overview" },
    { href: "/account", label: "Account", icon: "gear" },
  ];
  if (systemRoles.includes(SYSTEM_OWNER_ROLE)) {
    links.push({ href: "/users", label: "Users", icon: "users" });
  }
  return links;
}
