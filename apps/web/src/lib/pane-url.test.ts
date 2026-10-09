import { afterEach, describe, expect, it, vi } from "vitest";

import {
  closePane,
  initialPaneState,
  navigatePaneView,
  openPane,
  PANE_USER_DETAIL_PATH,
} from "@/lib/pane-state";
import {
  parsePaneParam,
  restorePaneState,
  serializePaneParam,
} from "@/lib/pane-url";
import { stubStorage } from "@/lib/storage-stub.testsupport";

const OWNER = ["system_owner"];

afterEach(() => vi.unstubAllGlobals());

describe("pane param contract", () => {
  it("parses chat and bare view paths", () => {
    expect(parsePaneParam("?pane=chat", "/chat", [])).toEqual({ kind: "chat" });
    expect(parsePaneParam("?pane=view:/users", "/chat", OWNER)).toEqual({
      kind: "view",
      viewPath: "/users",
    });
  });

  it("drops unknown, extra-segment, and non-view values", () => {
    for (const raw of [
      "view:/bogus",
      "view:/users/42",
      "view:/users/detail/42",
      "view:/chat",
      "view:",
      "chat:all",
      "View:/users",
      "",
    ]) {
      expect(parsePaneParam(`?pane=${raw}`, "/chat", OWNER), raw).toBeNull();
    }
  });

  it("survives URL encoding round trips", () => {
    const params = new URLSearchParams({ pane: "view:/users" });
    expect(parsePaneParam(params.toString(), "/chat", OWNER)).toEqual({
      kind: "view",
      viewPath: "/users",
    });
  });

  it("ignores the param off the chat-surface routes", () => {
    expect(parsePaneParam("?pane=chat", "/docs", OWNER)).toBeNull();
  });
});

// The detail path is pane-internal: it must never reach a shared URL.
describe("detail path never round-trips", () => {
  it("serializes an open detail view as its list path", () => {
    let state = openPane(initialPaneState(), { kind: "view", viewPath: "/users" }, OWNER);
    state = navigatePaneView(state, PANE_USER_DETAIL_PATH, OWNER, 42);
    expect(serializePaneParam(state)).toBe("view:/users");
  });

  it("restores a detail param as a fresh list with no selection", () => {
    expect(
      parsePaneParam(`?pane=view:${PANE_USER_DETAIL_PATH}`, "/chat", OWNER),
    ).toEqual({ kind: "view", viewPath: "/users" });
    const state = restorePaneState(
      `?pane=view:${PANE_USER_DETAIL_PATH}`,
      "/chat",
      OWNER,
    );
    expect(state).toMatchObject({
      kind: "view",
      viewPath: "/users",
      detailId: null,
    });
  });

  it("keeps the detail param owner-gated after normalization", () => {
    expect(
      parsePaneParam(`?pane=view:${PANE_USER_DETAIL_PATH}`, "/chat", []),
    ).toBeNull();
  });
});

describe("param round trips", () => {
  it("restores open state from the URL and serializes it back", () => {
    const state = restorePaneState("?pane=view%3A%2Fusers", "/users", OWNER);
    expect(state).toMatchObject({
      open: true,
      kind: "view",
      viewPath: "/users",
      backStack: [],
    });
    expect(serializePaneParam(state)).toBe("view:/users");
  });

  it("serializes a closed pane to no param", () => {
    let state = openPane(initialPaneState(), { kind: "view", viewPath: "/users" }, OWNER);
    state = closePane(state);
    expect(serializePaneParam(state)).toBeNull();
  });

  it("stays closed on a forbidden or absent param", () => {
    expect(restorePaneState("?pane=view:/users", "/chat", []).open).toBe(false);
    expect(restorePaneState("", "/chat", OWNER).open).toBe(false);
  });

  it("never writes the last-used seed on restore", () => {
    const store = stubStorage({ "taipan-pane-last": "chat" });
    const state = restorePaneState("?pane=view:/users", "/users", OWNER);
    expect(state.open).toBe(true);
    expect(store.get("taipan-pane-last")).toBe("chat");
  });

  it("still reads the stored ratio on restore", () => {
    stubStorage({ "taipan-pane-ratio": "0.7" });
    expect(restorePaneState("?pane=chat", "/chat", []).ratio).toBe(0.7);
  });
});
