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

// Sidebar sections for non-chat private routes. The chat surface carries no
// shell nav of its own; the system section exists only for system_owner.
export function privateNav(systemRoles: string[]): NavSection[] {
  const sections: NavSection[] = [];
  if (systemRoles.includes(SYSTEM_OWNER_ROLE)) {
    sections.push({
      heading: "system",
      items: [
        { href: "/users", label: "users", icon: "users" },
        { href: "/settings", label: "settings", icon: "gear" },
      ],
    });
  }
  return sections;
}

// Links composed into the OpenUI chat sidebar above the thread list.
// Members get none: the chat plus its threads is the whole member surface.
export function chatNavLinks(systemRoles: string[]): NavItem[] {
  if (!systemRoles.includes(SYSTEM_OWNER_ROLE)) return [];
  return [
    { href: "/users", label: "users", icon: "users" },
    { href: "/settings", label: "settings", icon: "gear" },
  ];
}
