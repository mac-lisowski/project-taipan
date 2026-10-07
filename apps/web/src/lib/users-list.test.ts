import { afterEach, describe, expect, it, vi } from "vitest";
import { formatDate, loadUsers, reduceUsersView, USERS_PATH } from "./users-list";

const OWNER_DENIED = JSON.stringify({ detail: "system owner role required" });
const ROW = {
  id: 1,
  email: "ada@example.com",
  is_active: true,
  created_at: "2026-10-01T09:15:00Z",
};

describe("loadUsers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETs the same-origin users path and maps the body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify([ROW]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadUsers();

    expect(fetchMock).toHaveBeenCalledWith(USERS_PATH);
    expect(result).toEqual({ ok: true, users: [ROW] });
  });

  it("surfaces the upstream detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(OWNER_DENIED, { status: 403 })),
    );
    expect(await loadUsers()).toEqual({
      ok: false,
      error: "system owner role required",
    });
  });

  it("maps a non-list body to an error instead of throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 200 })),
    );
    expect(await loadUsers()).toEqual({ ok: false, error: "unexpected users body" });
  });

  it("maps a thrown fetch to a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await loadUsers()).toEqual({ ok: false, error: "network error" });
  });
});

describe("reduceUsersView", () => {
  it("lands a good load as ready", () => {
    const view = reduceUsersView(
      { state: "loading" },
      { type: "loaded", result: { ok: true, users: [ROW] } },
    );
    expect(view).toEqual({ state: "ready", users: [ROW] });
  });

  it("carries a load failure into the error state", () => {
    const view = reduceUsersView(
      { state: "loading" },
      { type: "loaded", result: { ok: false, error: "network error" } },
    );
    expect(view).toEqual({ state: "error", message: "network error" });
  });
});

describe("formatDate", () => {
  it("renders date only ISO", () => {
    expect(formatDate("2026-10-01T09:15:00Z")).toBe("2026-10-01");
  });
});
