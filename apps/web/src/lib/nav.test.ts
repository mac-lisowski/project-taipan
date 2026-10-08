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
  it("gives members no links: chat plus threads is their surface", () => {
    expect(chatNavLinks([])).toEqual([]);
    expect(chatNavLinks(["admin", "member"])).toEqual([]);
  });

  it("gives system_owner the management links", () => {
    expect(chatNavLinks(["system_owner"])).toEqual([
      { href: "/users", label: "users", icon: "users" },
      { href: "/settings", label: "settings", icon: "gear" },
    ]);
  });
});
