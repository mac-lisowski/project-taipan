import { describe, expect, it } from "vitest";

import {
  initialPaneState,
  openPane,
  paneBack,
  PANE_USER_DETAIL_PATH,
  type PaneState,
} from "@/lib/pane-state";
import { paneNavigate, paneNavWrite, splitTargetPath } from "@/lib/shell-nav";

const OWNER = ["system_owner"];

function openView(viewPath: string, roles: string[] = OWNER): PaneState {
  return openPane(initialPaneState(), { kind: "view", viewPath }, roles);
}

describe("splitTargetPath", () => {
  it("splits the route path from the user param", () => {
    expect(splitTargetPath("/users")).toEqual({ pathname: "/users", user: null });
    expect(splitTargetPath("/users?user=4&q=a")).toEqual({ pathname: "/users", user: 4 });
    expect(splitTargetPath("/users?user=0")).toEqual({ pathname: "/users", user: null });
    expect(splitTargetPath("/account")).toEqual({ pathname: "/account", user: null });
  });
});

describe("paneNavWrite", () => {
  it("moves to a member view and records the back stack", () => {
    const next = paneNavWrite(openView("/dashboard", []), { path: "/account" }, []);
    expect(next.viewPath).toBe("/account");
    expect(next.backStack).toEqual([{ viewPath: "/dashboard", detailId: null }]);
  });

  it("lands a picked record on the pane detail path", () => {
    const next = paneNavWrite(
      openView("/users"),
      { path: "/users?user=7", detailId: 7, replace: true },
      OWNER,
    );
    expect(next.viewPath).toBe(PANE_USER_DETAIL_PATH);
    expect(next.detailId).toBe(7);
    // replace gates browser history only; the pane back stack still
    // records the move so the header back returns to the list.
    expect(next.backStack).toEqual([{ viewPath: "/users", detailId: null }]);
    expect(paneBack(next)).toMatchObject({ viewPath: "/users", detailId: null });
  });

  it("reads the detail from the user param when the field is absent", () => {
    const next = paneNavWrite(openView("/users"), { path: "/users?user=9" }, OWNER);
    expect(next).toMatchObject({ viewPath: PANE_USER_DETAIL_PATH, detailId: 9 });
  });

  it("writes a same-view detail change as a selection", () => {
    const detail = paneNavWrite(openView("/users"), { path: "/users?user=7" }, OWNER);
    const next = paneNavWrite(
      detail,
      { path: "/users?user=8", detailId: 8, replace: true },
      OWNER,
    );
    expect(next).toMatchObject({ viewPath: PANE_USER_DETAIL_PATH, detailId: 8 });
    expect(next.backStack).toEqual([
      { viewPath: "/users", detailId: null },
      { viewPath: PANE_USER_DETAIL_PATH, detailId: 7 },
    ]);
  });

  it("returns to the list when the detail clears", () => {
    const detail = paneNavWrite(openView("/users"), { path: "/users?user=7" }, OWNER);
    const next = paneNavWrite(detail, { path: "/users", detailId: null }, OWNER);
    expect(next).toMatchObject({ viewPath: "/users", detailId: null });
  });

  it("is a no-op for an identical location", () => {
    const list = openView("/users");
    expect(paneNavWrite(list, { path: "/users" }, OWNER)).toBe(list);
    expect(paneNavWrite(list, { path: "/users?q=x&page=2", replace: true }, OWNER)).toBe(
      list,
    );
  });

  it("refuses owner-only targets for non-owners", () => {
    const state = openView("/dashboard", []);
    for (const target of [
      { path: "/users" },
      { path: "/system/settings" },
      { path: "/users?user=3", detailId: 3 },
      { path: PANE_USER_DETAIL_PATH, detailId: 3 },
    ]) {
      expect(paneNavWrite(state, target, [])).toBe(state);
    }
    expect(paneNavWrite(state, { path: "/users" }, OWNER)).not.toBe(state);
  });

  it("refuses unknown and non-pane paths for everyone", () => {
    const state = openView("/dashboard");
    for (const path of ["/bogus", "/chat", "/users/detail/extra"]) {
      expect(paneNavWrite(state, { path }, OWNER)).toBe(state);
    }
  });

  it("refuses while the pane is closed or showing chat", () => {
    const closed = initialPaneState();
    expect(paneNavWrite(closed, { path: "/account" }, [])).toBe(closed);
    const chat = openPane(closed, { kind: "chat" });
    expect(paneNavWrite(chat, { path: "/account" }, [])).toBe(chat);
  });
});

describe("paneNavigate", () => {
  it("dispatches the written state to the host setter", () => {
    const writes: PaneState[] = [];
    const nav = paneNavigate(openView("/dashboard", []), [], (next) => writes.push(next));
    nav({ path: "/account" });
    expect(writes).toHaveLength(1);
    expect(writes[0]?.viewPath).toBe("/account");
  });

  it("dispatches nothing for a refused target", () => {
    const writes: PaneState[] = [];
    const nav = paneNavigate(openView("/dashboard", []), [], (next) => writes.push(next));
    nav({ path: "/users" });
    nav({ path: "/chat" });
    expect(writes).toEqual([]);
  });
});
