import { afterEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: mockGet,
  })),
}));

vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`NEXT_REDIRECT:${url}`);
  },
}));

const mockResolveAccount = vi.fn();
const mockRevokeSession = vi.fn();
vi.mock("../api/upstream", () => ({
  resolveAccount: (...args: unknown[]) => mockResolveAccount(...args),
  revokeSession: (...args: unknown[]) => mockRevokeSession(...args),
}));

import * as route from "./route";

describe("logout route", () => {
  afterEach(() => {
    mockGet.mockReset();
    mockResolveAccount.mockReset();
    mockRevokeSession.mockReset();
  });

  it("exposes no GET handler, so link prefetch cannot log users out", () => {
    expect(route).not.toHaveProperty("GET");
  });

  it("POST revokes the session and clears the cookie without redirecting", async () => {
    mockGet.mockReturnValue({ name: "session", value: "tok-123" });
    const res = await route.POST();
    expect(res.status).toBe(204);
    expect(res.headers.get("location")).toBeNull();
    expect(mockRevokeSession).toHaveBeenCalledWith("tok-123");
    const cleared = res.headers.getSetCookie().join("; ");
    expect(cleared).toContain("session=;");
    expect(cleared).toContain("Max-Age=0");
  });

  it("POST without a session still answers 204", async () => {
    mockGet.mockReturnValue(undefined);
    const res = await route.POST();
    expect(res.status).toBe(204);
    expect(mockRevokeSession).not.toHaveBeenCalled();
  });
});
