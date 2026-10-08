import { afterEach, describe, expect, it, vi } from "vitest";
import { RESET_LANDING, submitReset } from "./reset-password";

describe("submitReset", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts token and new_password as JSON to /api/auth/reset", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitReset("raw-token", "new-password-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: "raw-token", new_password: "new-password-1" }),
    });
  });

  it("returns ok on success and RESET_LANDING is chat", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await submitReset("raw-token", "new-password-1")).toEqual({
      ok: true,
      data: null,
    });
    expect(RESET_LANDING).toBe("/chat");
  });

  it("surfaces the 400 detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "invalid or expired reset link" }), {
          status: 400,
        }),
      ),
    );
    expect(await submitReset("raw-token", "new-password-1")).toEqual({
      ok: false,
      error: "invalid or expired reset link",
    });
  });

  it("surfaces the 422 detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "weak password" }), { status: 422 }),
      ),
    );
    expect(await submitReset("raw-token", "short")).toEqual({
      ok: false,
      error: "weak password",
    });
  });

  it("falls back to the generic error when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await submitReset("raw-token", "new-password-1")).toEqual({
      ok: false,
      error: "network error",
    });
  });
});
