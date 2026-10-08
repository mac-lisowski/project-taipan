import { afterEach, describe, expect, it, vi } from "vitest";
import { NextResponse } from "next/server";
import type { Me } from "../app/api/upstream";
import {
  clearSessionCookie,
  getSessionToken,
  hasSession,
  redirectIfAuthenticated,
  requireAccount,
  sessionCookieHeader,
  terminateSession,
} from "./session";

const mockGet = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: mockGet,
  })),
}));

const mockRedirect = vi.fn((url: string) => {
  throw new Error(`NEXT_REDIRECT:${url}`);
});
vi.mock("next/navigation", () => ({
  redirect: (url: string) => mockRedirect(url),
}));

const mockResolveAccount = vi.fn();
const mockRevokeSession = vi.fn();
vi.mock("../app/api/upstream", () => ({
  resolveAccount: (...args: unknown[]) => mockResolveAccount(...args),
  revokeSession: (...args: unknown[]) => mockRevokeSession(...args),
}));

describe("session helpers", () => {
  afterEach(() => {
    mockGet.mockReset();
    mockRedirect.mockClear();
    mockResolveAccount.mockReset();
    mockRevokeSession.mockReset();
  });

  it("formats session cookie header", () => {
    expect(sessionCookieHeader("tok-123")).toBe("session=tok-123");
  });

  it("getSessionToken returns token when present", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    const token = await getSessionToken();
    expect(token).toBe("tok-123");
    expect(mockGet).toHaveBeenCalledWith("session");
  });

  it("getSessionToken returns undefined when missing", async () => {
    mockGet.mockReturnValue(undefined);
    const token = await getSessionToken();
    expect(token).toBeUndefined();
    expect(mockGet).toHaveBeenCalledWith("session");
  });

  it("hasSession returns true when present", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    expect(await hasSession()).toBe(true);
  });

  it("hasSession returns false when missing", async () => {
    mockGet.mockReturnValue(undefined);
    expect(await hasSession()).toBe(false);
  });

  it("clearSessionCookie sets empty cookie with maxAge 0", () => {
    const res = new NextResponse();
    clearSessionCookie(res);
    const cookie = res.cookies.get("session");
    expect(cookie?.value).toBe("");
    expect(cookie?.maxAge).toBe(0);
    expect(cookie?.path).toBe("/");
  });

  it("requireAccount returns account identity when authenticated", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    const me: Me = {
      id: 1,
      email: "a@x.com",
      tenant_id: "t1",
      roles: ["admin"],
      system_roles: ["system_owner"],
    };
    mockResolveAccount.mockResolvedValue({ me });

    const result = await requireAccount();
    expect(result).toEqual(me);
    expect(mockResolveAccount).toHaveBeenCalledWith("tok-123");
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("requireAccount redirects when unauthenticated", async () => {
    mockGet.mockReturnValue(undefined);
    mockResolveAccount.mockResolvedValue({ redirect: "/" });

    await expect(requireAccount()).rejects.toThrow("NEXT_REDIRECT:/");
    expect(mockResolveAccount).toHaveBeenCalledWith(undefined);
    expect(mockRedirect).toHaveBeenCalledWith("/");
  });

  it("requireAccount redirects when token is invalid or expired", async () => {
    mockGet.mockReturnValue({ name: "session", value: "expired-tok" });
    mockResolveAccount.mockResolvedValue({ redirect: "/" });

    await expect(requireAccount()).rejects.toThrow("NEXT_REDIRECT:/");
    expect(mockResolveAccount).toHaveBeenCalledWith("expired-tok");
    expect(mockRedirect).toHaveBeenCalledWith("/");
  });

  it("redirectIfAuthenticated redirects when session exists", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    await expect(redirectIfAuthenticated("/account")).rejects.toThrow(
      "NEXT_REDIRECT:/account",
    );
    expect(mockRedirect).toHaveBeenCalledWith("/account");
  });

  it("redirectIfAuthenticated defaults to chat", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    await expect(redirectIfAuthenticated()).rejects.toThrow(
      "NEXT_REDIRECT:/chat",
    );
    expect(mockRedirect).toHaveBeenCalledWith("/chat");
  });

  it("redirectIfAuthenticated does nothing when no session exists", async () => {
    mockGet.mockReturnValue(undefined);
    await redirectIfAuthenticated("/account");
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("terminateSession revokes upstream and clears cookie", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    mockRevokeSession.mockResolvedValue(undefined);

    const res = new NextResponse();
    await terminateSession(res);

    expect(mockRevokeSession).toHaveBeenCalledWith("tok-123");
    const cookie = res.cookies.get("session");
    expect(cookie?.value).toBe("");
    expect(cookie?.maxAge).toBe(0);
    expect(cookie?.path).toBe("/");
  });

  it("terminateSession skips revoke and still clears cookie when no session exists", async () => {
    mockGet.mockReturnValue(undefined);

    const res = new NextResponse();
    await terminateSession(res);

    expect(mockRevokeSession).not.toHaveBeenCalled();
    const cookie = res.cookies.get("session");
    expect(cookie?.value).toBe("");
    expect(cookie?.maxAge).toBe(0);
    expect(cookie?.path).toBe("/");
  });
});
