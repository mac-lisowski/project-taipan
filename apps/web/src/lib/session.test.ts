import { afterEach, describe, expect, it, vi } from "vitest";
import { NextResponse } from "next/server";
import {
  clearSessionCookie,
  getSessionToken,
  hasSession,
  sessionCookieHeader,
} from "./session";

const mockGet = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: mockGet,
  })),
}));

describe("session helpers", () => {
  afterEach(() => {
    mockGet.mockReset();
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
});
