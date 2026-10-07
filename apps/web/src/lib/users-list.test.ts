import { afterEach, describe, expect, it, vi } from "vitest";
import {
  applyUsersQuery,
  filterUsersByStatus,
  formatDate,
  loadUsers,
  reduceUsersView,
  searchUsers,
  USERS_PATH,
} from "./users-list";

const OWNER_DENIED = JSON.stringify({ detail: "system owner role required" });
const ROW = {
  id: 1,
  email: "ada@example.com",
  is_active: true,
  created_at: "2026-10-01T09:15:00Z",
};
const INACTIVE_ROW = {
  id: 2,
  email: "grace@example.org",
  is_active: false,
  created_at: "2026-10-02T10:00:00Z",
};
const ROWS = [ROW, INACTIVE_ROW];

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
  it("lands a good load as ready with default controls", () => {
    const view = reduceUsersView(
      { state: "loading" },
      { type: "loaded", result: { ok: true, users: ROWS } },
    );
    expect(view).toEqual({
      state: "ready",
      users: ROWS,
      query: "",
      status: "all",
      page: 1,
    });
  });

  it("carries a load failure into the error state", () => {
    const view = reduceUsersView(
      { state: "loading" },
      { type: "loaded", result: { ok: false, error: "network error" } },
    );
    expect(view).toEqual({ state: "error", message: "network error" });
  });

  it("stores a query and resets the page", () => {
    const view = reduceUsersView(ready(ROWS, { query: "ada", page: 3 }), {
      type: "query_changed",
      query: "grace",
    });
    expect(view).toEqual({ ...ready(ROWS), query: "grace" });
  });

  it("stores a status and resets the page", () => {
    const view = reduceUsersView(ready(ROWS, { status: "active", page: 2 }), {
      type: "status_changed",
      status: "inactive",
    });
    expect(view).toEqual({ ...ready(ROWS), status: "inactive" });
  });

  it("ignores control changes before the list is ready", () => {
    const view = reduceUsersView({ state: "loading" }, {
      type: "query_changed",
      query: "ada",
    });
    expect(view).toEqual({ state: "loading" });
  });
});

function ready(
  users: typeof ROWS,
  over: Partial<{ query: string; status: "all" | "active" | "inactive"; page: number }> = {},
) {
  return {
    state: "ready" as const,
    users,
    query: "",
    status: "all" as const,
    page: 1,
    ...over,
  };
}

describe("searchUsers", () => {
  it("matches substrings ignoring letter case", () => {
    expect(searchUsers(ROWS, "GRACE")).toEqual([INACTIVE_ROW]);
    expect(searchUsers(ROWS, "example.org")).toEqual([INACTIVE_ROW]);
  });

  it("returns everything for a blank query", () => {
    expect(searchUsers(ROWS, "   ")).toEqual(ROWS);
  });
});

describe("filterUsersByStatus", () => {
  it("keeps only active users", () => {
    expect(filterUsersByStatus(ROWS, "active")).toEqual([ROW]);
  });

  it("keeps only inactive users", () => {
    expect(filterUsersByStatus(ROWS, "inactive")).toEqual([INACTIVE_ROW]);
  });

  it("passes everything through for all", () => {
    expect(filterUsersByStatus(ROWS, "all")).toEqual(ROWS);
  });
});

describe("applyUsersQuery", () => {
  it("chains search and status", () => {
    expect(applyUsersQuery(ROWS, "ada", "inactive")).toEqual([]);
    expect(applyUsersQuery(ROWS, "", "active")).toEqual([ROW]);
  });
});

describe("formatDate", () => {
  it("renders date only ISO", () => {
    expect(formatDate("2026-10-01T09:15:00Z")).toBe("2026-10-01");
  });
});
