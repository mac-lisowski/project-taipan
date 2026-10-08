import { afterEach, describe, expect, it, vi } from "vitest";
import {
  applyUsersQuery,
  clampPage,
  countLine,
  filterUsersByStatus,
  formatDate,
  loadUsers,
  pageCount,
  pageSlice,
  reduceUsersView,
  searchUsers,
  USERS_COPY,
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
    expect(result).toEqual({ ok: true, data: [ROW] });
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
      { type: "loaded", result: { ok: true, data: ROWS } },
    );
    expect(view).toEqual({
      state: "ready",
      users: ROWS,
      query: "",
      status: "all",
      page: 1,
      pageSize: 10,
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

  it("stores a page size and resets the page", () => {
    // Thirty rows on page 3 of size 10 still fit page 2 of size 25, so a
    // clamp-only implementation would fail this; reset must land on one.
    const users = Array.from({ length: 30 }, (_, i) => ({
      ...ROW,
      id: i + 1,
    }));
    const view = reduceUsersView(ready(users, { pageSize: 10, page: 3 }), {
      type: "page_size_changed",
      pageSize: 25,
    });
    expect(view).toEqual({ ...ready(users), pageSize: 25 });
  });

  it("clamps a page change into the list bounds", () => {
    const view = reduceUsersView(ready(ROWS, { pageSize: 10, page: 1 }), {
      type: "page_changed",
      page: 99,
    });
    expect(view).toEqual({ ...ready(ROWS), page: 1 });
  });

  it("clamps a page change against the filtered count", () => {
    // Ten active rows of twenty five: the filtered list has one page of
    // ten, so a clamp against the unfiltered total would answer three.
    const users = [
      ...Array.from({ length: 10 }, (_, i) => ({ ...ROW, id: i + 1 })),
      ...Array.from({ length: 15 }, (_, i) => ({ ...INACTIVE_ROW, id: i + 11 })),
    ];
    const view = reduceUsersView(
      ready(users, { status: "active", pageSize: 10, page: 1 }),
      { type: "page_changed", page: 99 },
    );
    expect(view).toEqual({ ...ready(users, { status: "active" }), page: 1 });
  });

  it("sends the view back to loading on retry", () => {
    const view = reduceUsersView(
      { state: "error", message: "network error" },
      { type: "retry" },
    );
    expect(view).toEqual({ state: "loading" });
  });
});

function ready(
  users: typeof ROWS,
  over: Partial<{
    query: string;
    status: "all" | "active" | "inactive";
    page: number;
    pageSize: 10 | 25 | 50;
  }> = {},
) {
  return {
    state: "ready" as const,
    users,
    query: "",
    status: "all" as const,
    page: 1,
    pageSize: 10 as const,
    ...over,
  };
}

describe("paging helpers", () => {
  it("counts pages with an exact division edge", () => {
    expect(pageCount(0, 10)).toBe(1);
    expect(pageCount(20, 10)).toBe(2);
    expect(pageCount(21, 10)).toBe(3);
  });

  it("clamps a page index into bounds", () => {
    expect(clampPage(0, 25, 10)).toBe(1);
    expect(clampPage(99, 25, 10)).toBe(3);
    expect(clampPage(2, 0, 10)).toBe(1);
  });

  it("slices the middle page", () => {
    const users = Array.from({ length: 25 }, (_, i) => ({
      ...ROW,
      id: i + 1,
    }));
    expect(pageSlice(users, 2, 10).map((u) => u.id)).toEqual([
      11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    ]);
  });

  it("clamps the slice for a past-end page", () => {
    expect(pageSlice(ROWS, 99, 10)).toEqual(ROWS);
  });
});

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

describe("pinned copy", () => {
  it("keeps the screen strings exact", () => {
    expect(USERS_COPY.loading).toBe("loading…");
    expect(USERS_COPY.empty).toBe("no users match");
    expect(USERS_COPY.retry).toBe("retry");
  });

  it("formats the count line", () => {
    expect(countLine(42, 60)).toBe("42 of 60 users");
  });
});
