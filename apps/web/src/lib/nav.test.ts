import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { CHAT_SURFACE_ROUTES, chatNavLinks, privateNav } from "@/lib/nav";

const here = dirname(fileURLToPath(import.meta.url));
const readSource = (fromHere: string): string =>
  readFileSync(resolve(here, fromHere), "utf8");

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
          { href: "/system/settings", label: "settings", icon: "gear" },
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

// A chat route missing from CHAT_SURFACE_ROUTES renders outside
// ShellAccountProvider and 500s on useShellAccount, so the list is
// checked against the route registrations themselves.
describe("chat surface routes", () => {
  it("lists the chat root itself", () => {
    expect(CHAT_SURFACE_ROUTES).toContain("/chat");
  });

  it("covers every AgentInterface.Route registered in chat-app", () => {
    const registered = [
      ...readSource("../components/chat/chat-app.tsx").matchAll(
        /AgentInterface\.Route\s+path="([^"]+)"/g,
      ),
    ].map((match) => match[1]);
    expect(registered.length).toBeGreaterThan(0);
    for (const path of registered) {
      expect(
        CHAT_SURFACE_ROUTES,
        `${path} renders full-viewport but is missing from CHAT_SURFACE_ROUTES`,
      ).toContain(path);
    }
  });

  it("is consumed by the private shell, not re-declared there", () => {
    const shell = readSource("../components/shell/private-shell.tsx");
    // The import line is the contract: the shell reads the one shared
    // list. Any inline route collection there would fork the source of
    // truth, so both shapes are forbidden outright.
    expect(shell).toMatch(
      /import\s*\{[^}]*CHAT_SURFACE_ROUTES[^}]*\}\s*from\s*"@\/lib\/nav"/,
    );
    expect(shell).not.toMatch(/new Set\(\[/);
    expect(shell).not.toMatch(/\[\s*"\/chat"/);
  });
});
