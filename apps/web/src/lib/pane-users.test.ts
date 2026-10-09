import { describe, expect, it, vi } from "vitest";

import { fetchUsersPage } from "@/lib/pane-users";
import type { UsersFilters } from "@/lib/users-list";

const FILTERS: UsersFilters = {
  q: "ada",
  status: "active",
  page: 2,
  pageSize: 25,
  user: 7,
};

const USERS_PAGE = {
  items: [
    {
      id: 1,
      email: "ada@example.com",
      is_active: true,
      created_at: "2026-10-01T09:15:00Z",
    },
  ],
  total: 1,
  total_all: 2,
  page: 2,
  page_size: 25,
};

describe("fetchUsersPage", () => {
  it("requests the BFF route with API filter names", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(USERS_PAGE), { status: 200 }),
      );
    const read = await fetchUsersPage(FILTERS, fetchImpl);
    expect(read).toEqual({ ok: true, data: USERS_PAGE });
    // `user` is a view concern; it must never reach the list query.
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/users?q=ada&status=active&page=2&page_size=25",
      { cache: "no-store" },
    );
  });

  it("omits default params", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(USERS_PAGE), { status: 200 }),
      );
    await fetchUsersPage(
      { q: " ", status: "all", page: 1, pageSize: 10, user: null },
      fetchImpl,
    );
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/api/users");
  });

  it("maps a non-ok response to an error read", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(new Response("denied", { status: 403 }));
    expect(await fetchUsersPage(FILTERS, fetchImpl)).toEqual({
      ok: false,
      error: "users list failed (403)",
    });
  });

  it("rejects a wrong body shape", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify([USERS_PAGE]), { status: 200 }),
      );
    expect(await fetchUsersPage(FILTERS, fetchImpl)).toEqual({
      ok: false,
      error: "unexpected users page body",
    });
  });

  it("maps a thrown fetch to an error read", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("down"));
    expect(await fetchUsersPage(FILTERS, fetchImpl)).toEqual({
      ok: false,
      error: "users list failed",
    });
  });
});
