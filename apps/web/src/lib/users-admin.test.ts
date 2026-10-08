import { afterEach, describe, expect, it, vi } from "vitest";
import {
  deleteUser,
  loadUserDetail,
  reduceDetailView,
  setUserActive,
  USERS_ADMIN_COPY,
  type DetailView,
  type UserDetail,
} from "./users-admin";

const DETAIL: UserDetail = {
  id: 7,
  email: "ada@example.com",
  is_active: true,
  created_at: "2026-10-01T09:15:00Z",
  updated_at: "2026-10-02T10:00:00Z",
  profile: null,
  system_roles: [],
  tenants: [{ tenant_id: "t1", roles: ["member"] }],
};

type ReadyView = Extract<DetailView, { state: "ready" }>;

function ready(over: Partial<ReadyView> = {}): ReadyView {
  return {
    state: "ready",
    user: DETAIL,
    pending: null,
    confirmingDelete: false,
    activationError: null,
    deleteError: null,
    deleted: false,
    ...over,
  };
}

describe("loadUserDetail", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETs the user detail path and maps the body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(DETAIL), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadUserDetail(7);

    expect(fetchMock).toHaveBeenCalledWith("/api/users/7");
    expect(result).toEqual({ ok: true, data: DETAIL });
  });

  it("surfaces the upstream detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "system owner role required" }), { status: 403 }),
      ),
    );
    expect(await loadUserDetail(7)).toEqual({
      ok: false,
      error: "system owner role required",
    });
  });

  it("maps a thrown fetch to a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await loadUserDetail(7)).toEqual({ ok: false, error: "network error" });
  });
});

describe("setUserActive", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("PUTs the activation flag and maps the body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ...DETAIL, is_active: false }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await setUserActive(7, false);

    expect(fetchMock).toHaveBeenCalledWith("/api/users/7/activation", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: false }),
    });
    expect(result).toEqual({ ok: true, data: { isActive: false } });
  });

  it("carries the API error verbatim on denial", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "cannot change your own account" }), {
          status: 409,
        }),
      ),
    );
    expect(await setUserActive(7, false)).toEqual({
      ok: false,
      error: "cannot change your own account",
    });
  });
});

describe("deleteUser", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("DELETEs the user path and maps 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await deleteUser(7);

    expect(fetchMock).toHaveBeenCalledWith("/api/users/7", { method: "DELETE" });
    expect(result).toEqual({ ok: true, data: null });
  });

  it("carries the API error on denial", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "cannot remove the last active owner" }), {
          status: 409,
        }),
      ),
    );
    expect(await deleteUser(7)).toEqual({
      ok: false,
      error: "cannot remove the last active owner",
    });
  });
});

describe("reduceDetailView", () => {
  it("lands a good load as ready", () => {
    const view = reduceDetailView(
      { state: "loading" },
      { type: "loaded", result: { ok: true, data: DETAIL } },
    );
    expect(view).toEqual(ready());
  });

  it("carries a load failure into the error state", () => {
    const view = reduceDetailView(
      { state: "loading" },
      { type: "loaded", result: { ok: false, error: "network error" } },
    );
    expect(view).toEqual({ state: "error", message: "network error" });
  });

  it("a reload reopens the load state and resets the confirm", () => {
    const view = reduceDetailView(ready({ confirmingDelete: true }), { type: "reload" });
    expect(view).toEqual({ state: "loading" });
  });

  it("marks activation in flight and clears its error", () => {
    const view = reduceDetailView(ready({ activationError: "old" }), {
      type: "activate_started",
    });
    expect(view).toEqual(ready({ pending: "activation" }));
  });

  it("merges an activation result into the detail", () => {
    const withProfile = ready({
      user: {
        ...DETAIL,
        profile: {
          display_name: "Ada",
          avatar_url: null,
          bio: null,
          created_at: "2026-10-01T09:15:00Z",
          updated_at: "2026-10-01T09:15:00Z",
        },
      },
      pending: "activation",
    });
    const view = reduceDetailView(withProfile, {
      type: "activate_finished",
      result: { ok: true, data: { isActive: false } },
    });
    expect(view).toEqual(
      ready({
        user: { ...withProfile.user, is_active: false },
      }),
    );
  });

  it("keeps the prior state and shows the error when activation fails", () => {
    const view = reduceDetailView(ready({ pending: "activation" }), {
      type: "activate_finished",
      result: { ok: false, error: "cannot change your own account" },
    });
    expect(view).toEqual(
      ready({ activationError: "cannot change your own account" }),
    );
  });

  it("marks delete in flight and clears the confirm", () => {
    const view = reduceDetailView(ready({ confirmingDelete: true }), {
      type: "delete_started",
    });
    expect(view).toEqual(ready({ pending: "delete" }));
  });

  it("signals deletion on success", () => {
    const view = reduceDetailView(ready({ pending: "delete" }), {
      type: "delete_finished",
      result: { ok: true, data: null },
    });
    expect(view).toEqual(ready({ pending: "delete", deleted: true }));
  });

  it("keeps the account and shows the error when delete fails", () => {
    const view = reduceDetailView(ready({ pending: "delete" }), {
      type: "delete_finished",
      result: { ok: false, error: "cannot remove the last active owner" },
    });
    expect(view).toEqual(ready({ deleteError: "cannot remove the last active owner" }));
  });

  it("tracks the two-click confirm", () => {
    const armed = reduceDetailView(ready(), {
      type: "delete_confirm_changed",
      confirming: true,
    });
    expect(armed).toEqual(ready({ confirmingDelete: true }));
    const cleared = reduceDetailView(armed, {
      type: "delete_confirm_changed",
      confirming: false,
    });
    expect(cleared).toEqual(ready());
  });

  it("ignores a stale activation finish", () => {
    const view = reduceDetailView(ready(), {
      type: "activate_finished",
      result: { ok: true, data: { isActive: false } },
    });
    expect(view).toEqual(ready());
  });

  it("rejects a body without an email as unexpected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 200 })),
    );
    expect(await loadUserDetail(7)).toEqual({ ok: false, error: "unexpected user body" });
  });
});

describe("pinned copy", () => {
  it("keeps the screen strings exact", () => {
    expect(USERS_ADMIN_COPY.loading).toBe("loading…");
    expect(USERS_ADMIN_COPY.delete).toBe("delete");
    expect(USERS_ADMIN_COPY.confirmDelete).toBe("confirm delete");
    expect(USERS_ADMIN_COPY.activate).toBe("activate");
    expect(USERS_ADMIN_COPY.deactivate).toBe("deactivate");
    expect(USERS_ADMIN_COPY.noProfile).toBe("no profile");
    expect(USERS_ADMIN_COPY.back).toBe("back to users");
  });
});
