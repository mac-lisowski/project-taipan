import { describe, expect, it } from "vitest";
import {
  countLine,
  filtersToParams,
  formatDate,
  guardUsersPage,
  pageCount,
  PAGE_SIZES,
  parseUsersFilters,
  usersPath,
  USERS_COPY,
  type UsersFilters,
} from "./users-list";

const ROW = {
  id: 1,
  email: "ada@example.com",
  is_active: true,
  created_at: "2026-10-01T09:15:00Z",
};

const PAGE = {
  items: [ROW],
  total: 41,
  total_all: 60,
  page: 2,
  page_size: 10,
};

const FILTERS: UsersFilters = {
  q: "ada",
  status: "active",
  page: 3,
  pageSize: 25,
  user: null,
};

describe("parseUsersFilters", () => {
  it("falls back to defaults on an empty param set", () => {
    expect(parseUsersFilters({})).toEqual({
      q: "",
      status: "all",
      page: 1,
      pageSize: 10,
      user: null,
    });
  });

  it("normalizes garbage to defaults instead of leaking a 422", () => {
    expect(
      parseUsersFilters({
        status: "bogus",
        size: "7",
        page: "0",
        user: "abc",
        q: ["array"],
      }),
    ).toEqual({ q: "", status: "all", page: 1, pageSize: 10, user: null });
    expect(parseUsersFilters({ page: "-3" }).page).toBe(1);
    expect(parseUsersFilters({ page: "NaN" }).page).toBe(1);
    expect(parseUsersFilters({ user: "0" }).user).toBe(null);
  });

  it("accepts every valid value", () => {
    expect(parseUsersFilters({ q: "ada", status: "inactive", page: "4", size: "50", user: "9" })).toEqual(
      { q: "ada", status: "inactive", page: 4, pageSize: 50, user: 9 },
    );
  });

  it("caps q at 200 characters", () => {
    expect(parseUsersFilters({ q: "x".repeat(500) }).q).toHaveLength(200);
  });
});

describe("filtersToParams and usersPath", () => {
  it("omits defaults so a clean /users means page one", () => {
    const clean: UsersFilters = { q: "", status: "all", page: 1, pageSize: 10, user: null };
    expect(filtersToParams(clean).size).toBe(0);
    expect(usersPath(clean)).toBe("/users");
  });

  it("keeps every non-default", () => {
    expect([...filtersToParams({ ...FILTERS, user: 7 }).entries()]).toEqual([
      ["q", "ada"],
      ["status", "active"],
      ["page", "3"],
      ["size", "25"],
      ["user", "7"],
    ]);
    expect(usersPath(FILTERS)).toBe("/users?q=ada&status=active&page=3&size=25");
  });

  it("round trips through parsing", () => {
    const filters = { ...FILTERS, user: 5 };
    const params = Object.fromEntries(filtersToParams(filters).entries());
    expect(parseUsersFilters(params)).toEqual(filters);
  });
});

describe("guardUsersPage", () => {
  it("accepts a well formed page", () => {
    expect(guardUsersPage(PAGE)).toEqual(PAGE);
  });

  it("rejects wrong shapes instead of crashing the table", () => {
    expect(guardUsersPage(null)).toBe(null);
    expect(guardUsersPage("nope")).toBe(null);
    expect(guardUsersPage({})).toBe(null);
    expect(guardUsersPage({ ...PAGE, items: "nope" })).toBe(null);
    expect(guardUsersPage({ ...PAGE, items: [{ ...ROW, email: 5 }] })).toBe(null);
    expect(guardUsersPage({ ...PAGE, total: "41" })).toBe(null);
    expect(guardUsersPage({ ...PAGE, page: 0 })).toBe(null);
  });
});

describe("pageCount", () => {
  it("reports one page for an empty total", () => {
    expect(pageCount(0, 10)).toBe(1);
  });

  it("rounds up across every page size", () => {
    for (const size of PAGE_SIZES) {
      expect(pageCount(1, size)).toBe(1);
      expect(pageCount(size, size)).toBe(1);
      expect(pageCount(size + 1, size)).toBe(2);
    }
    expect(pageCount(101, 50)).toBe(3);
  });
});

describe("pinned copy", () => {
  it("holds the exact screen strings", () => {
    expect(USERS_COPY.error).toBe("err");
    expect(USERS_COPY.empty).toBe("no users match");
    expect(USERS_COPY.retry).toBe("retry");
    expect(countLine(41, 60)).toBe("41 of 60 users");
    expect(formatDate("2026-10-01T09:15:00Z")).toBe("2026-10-01");
  });
});
