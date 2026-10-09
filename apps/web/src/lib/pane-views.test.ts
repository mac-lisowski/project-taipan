import { describe, expect, it } from "vitest";

import {
  initialPaneState,
  openPane,
  PANE_VIEW_PATHS,
} from "@/lib/pane-state";
import { paneTitle, paneViewFor } from "@/lib/pane-views";

const OWNER = ["system_owner"];

function viewState(viewPath: string) {
  return openPane(initialPaneState(), { kind: "view", viewPath }, OWNER);
}

describe("pane view table", () => {
  it("covers every allowed pane path", () => {
    for (const path of PANE_VIEW_PATHS) {
      expect(paneViewFor(path), path).not.toBeNull();
    }
  });

  it("maps each path to its view id", () => {
    expect(paneViewFor("/dashboard")?.id).toBe("overview");
    expect(paneViewFor("/users")?.id).toBe("users");
    expect(paneViewFor("/users/detail")?.id).toBe("user-detail");
    expect(paneViewFor("/system/settings")?.id).toBe("settings");
    expect(paneViewFor("/account")?.id).toBe("account");
  });

  it("drops unknown and extra-segment paths", () => {
    expect(paneViewFor("/chat")).toBeNull();
    expect(paneViewFor("/users/detail/extra")).toBeNull();
    expect(paneViewFor("/settings")).toBeNull();
    expect(paneViewFor("view:/users")).toBeNull();
    expect(paneViewFor(null)).toBeNull();
  });
});

describe("paneTitle", () => {
  it("names the chat kind", () => {
    expect(
      paneTitle(openPane(initialPaneState(), { kind: "chat" })),
    ).toBe("chat");
  });

  it("names each view", () => {
    expect(paneTitle(viewState("/dashboard"))).toBe("overview");
    expect(paneTitle(viewState("/users"))).toBe("users");
    expect(paneTitle(viewState("/system/settings"))).toBe("system settings");
  });

  it("names the closed default kind and falls back on a bad view path", () => {
    expect(paneTitle(initialPaneState())).toBe("chat");
    expect(
      paneTitle({
        ...initialPaneState(),
        open: true,
        kind: "view",
        viewPath: "/bogus",
      }),
    ).toBe("pane");
  });
});
