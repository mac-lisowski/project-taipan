import { afterEach, describe, expect, it, vi } from "vitest";

import {
  canOpenPanePath,
  clampPaneRatio,
  closePane,
  DEFAULT_PANE_RATIO,
  initialPaneState,
  isOwnerOnlyPath,
  isPaneSurfacePath,
  isPaneViewPath,
  navigatePaneView,
  openPane,
  paneAllows,
  paneBack,
  PANE_USER_DETAIL_PATH,
  readLastPaneContent,
  readPaneRatio,
  selectPaneDetail,
  setPaneRatio,
} from "@/lib/pane-state";
import { stubStorage } from "@/lib/storage-stub.testsupport";

const OWNER = ["system_owner"];

afterEach(() => vi.unstubAllGlobals());

describe("open and close transitions", () => {
  it("starts closed with defaults", () => {
    const state = initialPaneState();
    expect(state).toEqual({
      open: false,
      kind: "chat",
      viewPath: null,
      detailId: null,
      ratio: DEFAULT_PANE_RATIO,
      backStack: [],
    });
    expect(paneAllows(state, "close")).toBe(false);
  });

  it("generic open defaults to chat when nothing is stored", () => {
    const state = openPane(initialPaneState(), null);
    expect(state).toMatchObject({ open: true, kind: "chat", viewPath: null });
  });

  it("generic open seeds the stored last-used content", () => {
    stubStorage({ "taipan-pane-last": "view:/dashboard" });
    const state = openPane(initialPaneState(), null);
    expect(state).toMatchObject({ kind: "view", viewPath: "/dashboard" });
  });

  it("explicit target wins over the stored last-used content", () => {
    stubStorage({ "taipan-pane-last": "view:/dashboard" });
    const state = openPane(initialPaneState(), { kind: "chat" });
    expect(state.kind).toBe("chat");
  });

  it("opening while open replaces content and resets the back stack", () => {
    let state = openPane(initialPaneState(), { kind: "view", viewPath: "/dashboard" }, OWNER);
    state = navigatePaneView(state, "/account", OWNER);
    state = openPane(state, { kind: "chat" });
    expect(state).toMatchObject({ kind: "chat", viewPath: null, backStack: [] });
  });

  it("close clears content and back stack", () => {
    let state = openPane(initialPaneState(), { kind: "view", viewPath: "/users" }, OWNER);
    state = navigatePaneView(state, PANE_USER_DETAIL_PATH, OWNER, 7);
    state = closePane(state);
    expect(state).toMatchObject({
      open: false,
      viewPath: null,
      detailId: null,
      backStack: [],
    });
    expect(closePane(state)).toBe(state);
  });
});

describe("pane path sets", () => {
  it("knows the view and surface paths", () => {
    expect(isPaneViewPath("/dashboard")).toBe(true);
    expect(isPaneViewPath("/account")).toBe(true);
    expect(isPaneViewPath(PANE_USER_DETAIL_PATH)).toBe(true);
    expect(isPaneViewPath("/chat")).toBe(false);
    expect(isPaneViewPath("/bogus")).toBe(false);
    expect(isPaneSurfacePath("/chat")).toBe(true);
    expect(isPaneSurfacePath("/docs")).toBe(false);
  });
});

describe("ratio", () => {
  it("persists picks and reads them back", () => {
    const store = stubStorage();
    const state = setPaneRatio(initialPaneState(), 0.7);
    expect(state.ratio).toBe(0.7);
    expect(store.get("taipan-pane-ratio")).toBe("0.7");
    expect(readPaneRatio()).toBe(0.7);
  });

  it("keeps malformed stored values on the default", () => {
    stubStorage({ "taipan-pane-ratio": "wide" });
    expect(readPaneRatio()).toBe(DEFAULT_PANE_RATIO);
  });

  it("clamps at both width floors and leaves the stored pick alone", () => {
    // 1600px container: 360px pane floor, 360px thread floor after a
    // 272px sidebar, so the pane tops out at 968px.
    expect(clampPaneRatio(0.05, 1600)).toBeCloseTo(360 / 1600);
    expect(clampPaneRatio(0.9, 1600)).toBeCloseTo(968 / 1600);
    expect(clampPaneRatio(0.5, 1600)).toBeCloseTo(0.5);
    // At 1264px the max ratio is exactly one half (spec example).
    expect(clampPaneRatio(0.9, 1264)).toBeCloseTo(0.5);
    expect(setPaneRatio(initialPaneState(), 0.9).ratio).toBe(0.9);
  });

  it("keeps the pane floor when both floors cannot fit", () => {
    expect(clampPaneRatio(0.5, 950)).toBeCloseTo(360 / 950);
    expect(clampPaneRatio(0.5, 0)).toBe(0.5);
    expect(clampPaneRatio(Number.NaN, 1600)).toBe(DEFAULT_PANE_RATIO);
  });
});

describe("localStorage persistence", () => {
  it("persists last-used content on every open, never an open flag", () => {
    const store = stubStorage();
    openPane(initialPaneState(), { kind: "view", viewPath: "/account" }, []);
    expect(store.get("taipan-pane-last")).toBe("view:/account");
    openPane(initialPaneState(), { kind: "chat" });
    expect(store.get("taipan-pane-last")).toBe("chat");
    for (const key of store.keys()) {
      expect(["taipan-pane-ratio", "taipan-pane-last"]).toContain(key);
    }
  });

  it("can open without persisting the last-used content", () => {
    const store = stubStorage();
    const state = openPane(
      initialPaneState(),
      { kind: "view", viewPath: "/account" },
      [],
      { persist: false },
    );
    expect(state.open).toBe(true);
    expect(store.has("taipan-pane-last")).toBe(false);
  });

  it("normalizes a stored detail seed to its list", () => {
    stubStorage({ "taipan-pane-last": `view:${PANE_USER_DETAIL_PATH}` });
    expect(readLastPaneContent()).toEqual({ kind: "view", viewPath: "/users" });
  });

  it("works in-session when storage is blocked", () => {
    stubStorage({}, true);
    const state = setPaneRatio(initialPaneState(), 0.8);
    expect(state.ratio).toBe(0.8);
    expect(openPane(state, { kind: "chat" }).open).toBe(true);
    expect(readLastPaneContent()).toBeNull();
  });
});

describe("role gate", () => {
  it("exposes the owner-only path set", () => {
    expect(isOwnerOnlyPath("/users")).toBe(true);
    expect(isOwnerOnlyPath("/system/settings")).toBe(true);
    expect(isOwnerOnlyPath(PANE_USER_DETAIL_PATH)).toBe(true);
    expect(isOwnerOnlyPath("/dashboard")).toBe(false);
    expect(isOwnerOnlyPath("/bogus")).toBe(false);
  });

  it("collects the owner-only paths", () => {
    expect(canOpenPanePath([], "/users")).toBe(false);
    expect(canOpenPanePath([], "/system/settings")).toBe(false);
    expect(canOpenPanePath([], PANE_USER_DETAIL_PATH)).toBe(false);
    expect(canOpenPanePath(["member", "admin"], "/users")).toBe(false);
    expect(canOpenPanePath(OWNER, "/users")).toBe(true);
    expect(canOpenPanePath(OWNER, "/system/settings")).toBe(true);
  });

  it("allows member paths for any roles and refuses unknown ones", () => {
    expect(canOpenPanePath([], "/dashboard")).toBe(true);
    expect(canOpenPanePath([], "/account")).toBe(true);
    expect(canOpenPanePath(OWNER, "/bogus")).toBe(false);
  });

  it("refuses an explicit owner-only open for non-owners", () => {
    const closed = initialPaneState();
    const target = { kind: "view" as const, viewPath: "/users" };
    expect(openPane(closed, target, [])).toBe(closed);
    expect(openPane(closed, target, OWNER).open).toBe(true);
  });

  it("falls back to the default when the seed became forbidden", () => {
    stubStorage({ "taipan-pane-last": "view:/users" });
    expect(openPane(initialPaneState(), null, []).kind).toBe("chat");
  });

  it("refuses in-pane navigation to owner-only paths", () => {
    const state = openPane(initialPaneState(), { kind: "view", viewPath: "/dashboard" }, []);
    expect(navigatePaneView(state, "/users", [])).toBe(state);
    expect(navigatePaneView(state, "/account", []).viewPath).toBe("/account");
  });
});

describe("back stack", () => {
  function openUsers() {
    return openPane(initialPaneState(), { kind: "view", viewPath: "/users" }, OWNER);
  }

  it("walks view navigation in order", () => {
    let state = openPane(initialPaneState(), { kind: "view", viewPath: "/dashboard" }, OWNER);
    state = navigatePaneView(state, "/account", OWNER);
    state = navigatePaneView(state, "/system/settings", OWNER);
    expect(paneAllows(state, "back")).toBe(true);
    state = paneBack(state);
    expect(state.viewPath).toBe("/account");
    state = paneBack(state);
    expect(state.viewPath).toBe("/dashboard");
    expect(state.backStack).toEqual([]);
    expect(paneAllows(state, "back")).toBe(false);
    expect(paneBack(state)).toBe(state);
  });

  it("carries detail selections through back navigation", () => {
    let state = navigatePaneView(openUsers(), PANE_USER_DETAIL_PATH, OWNER, 7);
    state = selectPaneDetail(state, 9);
    expect(state.detailId).toBe(9);
    state = paneBack(state);
    expect(state.detailId).toBe(7);
    state = paneBack(state);
    expect(state).toMatchObject({ viewPath: "/users", detailId: null });
  });

  it("resets on kind switch and close", () => {
    let state = navigatePaneView(openUsers(), "/account", OWNER);
    expect(openPane(state, { kind: "chat" }).backStack).toEqual([]);
    state = navigatePaneView(openUsers(), "/account", OWNER);
    expect(closePane(state).backStack).toEqual([]);
  });

  it("does not push for a no-op navigation", () => {
    expect(navigatePaneView(openUsers(), "/users", OWNER).backStack).toEqual([]);
  });

  it("gates selectDetail to detail-capable views", () => {
    const list = openUsers();
    expect(paneAllows(list, "selectDetail")).toBe(false);
    const detail = navigatePaneView(list, PANE_USER_DETAIL_PATH, OWNER, 3);
    expect(paneAllows(detail, "selectDetail")).toBe(true);
  });
});
