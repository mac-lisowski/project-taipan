import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveThreadsSeed, resolveUsersPage } from "./upstream";
import type { UsersFilters } from "@/lib/users-list";

const FILTERS: UsersFilters = {
  q: "ada",
  status: "active",
  page: 2,
  pageSize: 25,
  user: null,
};

const USERS_PAGE = {
  items: [
    { id: 1, email: "ada@example.com", is_active: true, created_at: "2026-10-01T09:15:00Z" },
  ],
  total: 1,
  total_all: 2,
  page: 1,
  page_size: 10,
};

describe("resolveUsersPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("answers no session without a fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await resolveUsersPage(undefined, FILTERS)).toEqual({
      ok: false,
      error: "no session",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches one page with the cookie and the URL filters", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(USERS_PAGE), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const read = await resolveUsersPage("tok", FILTERS);
    expect(read).toEqual({ ok: true, data: USERS_PAGE });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api:8000/api/users?q=ada&status=active&page=2&page_size=25",
      { headers: { Cookie: "session=tok" }, cache: "no-store" },
    );
  });

  it("omits default params from the upstream query", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(USERS_PAGE), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await resolveUsersPage("tok", {
      q: "  ",
      status: "all",
      page: 1,
      pageSize: 10,
      user: null,
    });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://api:8000/api/users");
  });

  it("maps an upstream detail message", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "down" }), { status: 502 })),
    );
    expect(await resolveUsersPage("tok", FILTERS)).toEqual({ ok: false, error: "down" });
  });

  it("rejects a wrong body shape instead of rendering it", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify([USERS_PAGE]), { status: 200 })),
    );
    expect(await resolveUsersPage("tok", FILTERS)).toEqual({
      ok: false,
      error: "unexpected users page body",
    });
  });

  it("maps a thrown fetch to an error read", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await resolveUsersPage("tok", FILTERS)).toEqual({
      ok: false,
      error: "users list failed",
    });
  });
});

describe("resolveThreadsSeed", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("answers null without a session", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await resolveThreadsSeed(undefined)).toBe(null);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches the first cursor page with the cookie", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const body = { threads: [{ id: "t1" }], nextCursor: "c2" };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(body), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await resolveThreadsSeed("tok")).toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith("http://api:8000/api/threads/get", {
      headers: { Cookie: "session=tok" },
      cache: "no-store",
    });
  });

  it("degrades to null on any failure shape", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("nope", { status: 500 })),
    );
    expect(await resolveThreadsSeed("tok")).toBe(null);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await resolveThreadsSeed("tok")).toBe(null);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ nope: 1 }), { status: 200 })),
    );
    expect(await resolveThreadsSeed("tok")).toBe(null);
  });
});
