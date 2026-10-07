import { afterEach, describe, expect, it, vi } from "vitest";
import {
  REGISTER_LANDING,
  chooseRegisterGate,
  showSignUpLink,
  submitActivation,
  submitRegister,
} from "./register";
import { RESET_LANDING } from "./reset-password";

const OPEN = { ok: true, enabled: true } as const;
const CLOSED = { ok: true, enabled: false } as const;
const UNKNOWN = { ok: false, error: "registration switch read failed" } as const;

describe("chooseRegisterGate", () => {
  it("closes the door as not-found when the switch is off", () => {
    expect(chooseRegisterGate(CLOSED)).toEqual({ view: "not-found" });
  });

  it("still serves the set-password view for a mailed link after the switch flips off", () => {
    expect(chooseRegisterGate(CLOSED, "raw-token")).toEqual({
      view: "set-password",
      token: "raw-token",
    });
  });

  it("renders the email form when on and no token is present", () => {
    expect(chooseRegisterGate(OPEN)).toEqual({ view: "email-form" });
  });

  it("renders the set password form when on and a token is present", () => {
    expect(chooseRegisterGate(OPEN, "raw-token")).toEqual({
      view: "set-password",
      token: "raw-token",
    });
  });

  it("renders nothing sign-up specific when the switch read is unknown", () => {
    expect(chooseRegisterGate(UNKNOWN)).toEqual({
      view: "error",
      message: "registration switch read failed",
    });
  });
});

describe("showSignUpLink", () => {
  it("shows the sign up link only on an open switch", () => {
    expect(showSignUpLink(OPEN)).toBe(true);
    expect(showSignUpLink(CLOSED)).toBe(false);
    expect(showSignUpLink(UNKNOWN)).toBe(false);
  });
});

describe("submitRegister", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the email to the same-origin register path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitRegister("a@b.c");

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "a@b.c" }),
    });
  });

  it("returns ok on the 204 so the form can show the mailed-link note", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await submitRegister("a@b.c")).toEqual({ ok: true, data: null });
  });

  it("surfaces the closed-door 404 detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "not found" }), { status: 404 }),
      ),
    );
    expect(await submitRegister("a@b.c")).toEqual({ ok: false, error: "not found" });
  });
});

describe("submitActivation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts token and password as JSON to the activate path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitActivation("raw-token", "password-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: "raw-token", password: "password-1" }),
    });
  });

  it("returns ok on the 204 session mint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await submitActivation("raw-token", "password-1")).toEqual({
      ok: true,
      data: null,
    });
  });

  it("surfaces the invalid or expired detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "invalid or expired activation link" }), {
          status: 400,
        }),
      ),
    );
    expect(await submitActivation("raw-token", "password-1")).toEqual({
      ok: false,
      error: "invalid or expired activation link",
    });
  });

  it("surfaces the weak-password 422 verbatim so a retry keeps the token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "weak password" }), { status: 422 }),
      ),
    );
    expect(await submitActivation("raw-token", "short")).toEqual({
      ok: false,
      error: "weak password",
    });
  });

  it("falls back to the network error when fetch throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await submitActivation("raw-token", "password-1")).toEqual({
      ok: false,
      error: "network error",
    });
  });
});

describe("shared landing rule", () => {
  it("lands activation on the same dashboard target as login and reset", () => {
    expect(REGISTER_LANDING).toBe("/dashboard");
    expect(REGISTER_LANDING).toBe(RESET_LANDING);
  });
});
