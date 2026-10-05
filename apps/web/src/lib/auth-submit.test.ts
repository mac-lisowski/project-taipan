import { afterEach, describe, expect, it, vi } from "vitest";
import { submitAuth } from "./auth-submit";

describe("submitAuth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts form fields as JSON to the endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const form = new FormData();
    form.set("email", "a@b.c");
    await submitAuth("/api/auth/login", form);

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "a@b.c" }),
    });
  });

  it("returns ok on 2xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 200 })));
    expect(await submitAuth("/api/auth/login", new FormData())).toEqual({ ok: true });
  });

  it("surfaces upstream detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "bad credentials" }), { status: 401 }),
      ),
    );
    expect(await submitAuth("/api/auth/login", new FormData())).toEqual({
      ok: false,
      error: "bad credentials",
    });
  });

  it("falls back to the status when the body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("nope", { status: 502 })));
    expect(await submitAuth("/api/auth/login", new FormData())).toEqual({
      ok: false,
      error: "request failed (502)",
    });
  });

  it("maps a thrown fetch to a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await submitAuth("/api/auth/login", new FormData())).toEqual({
      ok: false,
      error: "network error",
    });
  });
});
