import { afterEach, describe, expect, it, vi } from "vitest";
import {
  resolveAccount,
  resolveLanding,
  resolveRegistrationSwitch,
  revokeSession,
  type Me,
} from "./upstream";

const ME: Me = {
  id: 1,
  email: "op@x.com",
  tenant_id: "t1",
  roles: ["admin", "member"],
  system_roles: ["system_owner"],
};

describe("resolveRegistrationSwitch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("GETs the public switch per render with no-store", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ enabled: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await resolveRegistrationSwitch()).toEqual({ ok: true, data: { enabled: true } });
    expect(fetchMock).toHaveBeenCalledWith("http://api:8000/api/system/registration", {
      cache: "no-store",
    });
  });

  it("maps an off switch", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ enabled: false }), { status: 200 }),
      ),
    );
    expect(await resolveRegistrationSwitch()).toEqual({ ok: true, data: { enabled: false } });
  });

  it("reports an error instead of a guess when the read fails", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "down" }), { status: 502 })),
    );
    expect(await resolveRegistrationSwitch()).toEqual({
      ok: false,
      error: "registration switch read failed (502)",
    });
  });

  it("reports an error on an unexpected answer", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ enabled: "yes" }), { status: 200 }),
      ),
    );
    expect(await resolveRegistrationSwitch()).toEqual({
      ok: false,
      error: "registration switch gave an unexpected answer",
    });
  });

  it("maps a thrown fetch to an error instead of rejecting", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await resolveRegistrationSwitch()).toEqual({
      ok: false,
      error: "registration switch read failed",
    });
  });
});

describe("resolveAccount", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("goes to landing with no session cookie", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await resolveAccount(undefined)).toEqual({ redirect: "/" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("goes to landing on upstream 401", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await resolveAccount("tok")).toEqual({ redirect: "/" });
    expect(fetchMock).toHaveBeenCalledWith("http://api:8000/api/auth/me", {
      headers: { Cookie: "session=tok" },
      cache: "no-store",
    });
  });

  it("shows setup when the instance needs it", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ needs_setup: true }), { status: 200 })),
    );
    expect(await resolveLanding()).toEqual({ view: "setup" });
  });

  it("shows login when the instance is seeded", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ needs_setup: false }), { status: 200 })),
    );
    expect(await resolveLanding()).toEqual({ view: "login" });
  });

  it("shows an error instead of a form when the probe fails", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "down" }), { status: 502 })),
    );
    expect((await resolveLanding()).view).toBe("error");
  });

  it("shows an error on an unexpected probe answer", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ needs_setup: "yes" }), { status: 200 })),
    );
    expect((await resolveLanding()).view).toBe("error");
  });

  it("revokes the session upstream without throwing", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(revokeSession("tok")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith("http://api:8000/api/auth/logout", {
      method: "POST",
      headers: { Cookie: "session=tok" },
    });
  });

  it("still resolves when the upstream is down", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("down")),
    );
    await expect(revokeSession("tok")).resolves.toBeUndefined();
  });

  it("renders me on 200 and passes the cookie through", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://api:8000");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(ME), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await resolveAccount("tok")).toEqual({ me: ME });
    expect(fetchMock).toHaveBeenCalledWith("http://api:8000/api/auth/me", {
      headers: { Cookie: "session=tok" },
      cache: "no-store",
    });
  });
});
