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
  it("gives members the overview link only", () => {
    expect(chatNavLinks([])).toEqual([{ href: "/dashboard", label: "overview" }]);
    expect(chatNavLinks(["admin", "member"])).toEqual([
      { href: "/dashboard", label: "overview" },
    ]);
  });

  it("appends the management links for system_owner", () => {
    expect(chatNavLinks(["system_owner"])).toEqual([
      { href: "/dashboard", label: "overview" },
      { href: "/users", label: "users", icon: "users" },
      { href: "/settings", label: "settings", icon: "gear" },
    ]);
  });
});
