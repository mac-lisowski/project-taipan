import { describe, expect, it } from "vitest";

import { privateNav } from "@/lib/nav";

describe("privateNav", () => {
  it("returns the base section without system for no roles", () => {
    expect(privateNav([])).toEqual([
      {
        heading: null,
        items: [
          { href: "/dashboard", label: "dashboard" },
          { href: "/chat", label: "chat" },
          { href: "/account", label: "account" },
          { href: "/docs", label: "docs" },
        ],
      },
    ]);
  });

  it("keeps the base-only shape for tenant roles", () => {
    expect(privateNav(["admin", "member"])).toEqual(privateNav([]));
  });

  it("appends the system section for system_owner", () => {
    expect(privateNav(["admin", "member", "system_owner"])).toEqual([
      {
        heading: null,
        items: [
          { href: "/dashboard", label: "dashboard" },
          { href: "/chat", label: "chat" },
          { href: "/account", label: "account" },
          { href: "/docs", label: "docs" },
        ],
      },
      {
        heading: "system",
        items: [
          { href: "/users", label: "users", icon: "users" },
          { href: "/settings", label: "settings", icon: "gear" },
        ],
      },
    ]);
  });

  it("ignores unknown roles", () => {
    expect(privateNav(["superadmin"])).toEqual(privateNav([]));
  });
});
