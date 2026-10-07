// The one system role the API grants today; keep in step with the backend enum.
export const SYSTEM_OWNER_ROLE = "system_owner";

export type NavItem = {
  href: string;
  label: string;
  icon?: "gear";
};

export type NavSection = {
  heading: string | null;
  items: NavItem[];
};

// Sidebar sections for private routes. The system section exists only for
// holders of the system_owner role; everyone else never sees it.
export function privateNav(systemRoles: string[]): NavSection[] {
  const sections: NavSection[] = [
    {
      heading: null,
      items: [
        { href: "/dashboard", label: "dashboard" },
        { href: "/account", label: "account" },
        { href: "/docs", label: "docs" },
      ],
    },
  ];
  if (systemRoles.includes(SYSTEM_OWNER_ROLE)) {
    sections.push({
      heading: "system",
      items: [{ href: "/settings", label: "settings", icon: "gear" }],
    });
  }
  return sections;
}
