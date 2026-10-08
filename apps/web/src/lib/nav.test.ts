import { describe, expect, it } from "vitest";

import { chatNavLinks, privateNav } from "@/lib/nav";

describe("privateNav", () => {
  it("returns no sections without system roles", () => {
    expect(privateNav([])).toEqual([]);
  });

  it("returns only the system section for system_owner", () => {
    expect(privateNav(["admin", "member", "system_owner"])).toEqual([
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
    expect(privateNav(["superadmin"])).toEqual([]);
  });
});

describe("chatNavLinks", () => {
  it("gives members overview and account", () => {
    expect(chatNavLinks([])).toEqual([
      { href: "/dashboard", label: "Overview" },
      { href: "/account", label: "Account", icon: "gear" },
    ]);
    expect(chatNavLinks(["admin", "member"])).toEqual([
      { href: "/dashboard", label: "Overview" },
      { href: "/account", label: "Account", icon: "gear" },
    ]);
  });

  it("appends users for system_owner; settings stays in the dropdown", () => {
    expect(chatNavLinks(["system_owner"])).toEqual([
      { href: "/dashboard", label: "Overview" },
      { href: "/account", label: "Account", icon: "gear" },
      { href: "/users", label: "Users", icon: "users" },
    ]);
  });
});
