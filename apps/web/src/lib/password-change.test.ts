import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MIN_PASSWORD_LENGTH,
  PASSWORD_RULES,
  changePassword,
  mismatchError,
  outcomeNote,
  ruleMet,
} from "./password-change";

function formWith(fields: Record<string, string>): FormData {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) form.set(key, value);
  return form;
}

describe("password change rules", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("states the API minimum length as the rule", () => {
    expect(MIN_PASSWORD_LENGTH).toBe(8);
  });

  it("mirrors the length gate for the display-only bar", () => {
    expect(ruleMet("1234567")).toBe(false);
    expect(ruleMet("12345678")).toBe(true);
  });

  it("accepts matching new fields", () => {
    expect(mismatchError("n3w-secret-456", "n3w-secret-456")).toBeNull();
  });

  it("gives a clear message for mismatched new fields", () => {
    expect(mismatchError("n3w-secret-456", "other-secret")).toBe(
      "new passwords do not match",
    );
  });

  it("blocks the submit on mismatch before any request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await changePassword(
      formWith({
        current_password: "old",
        new_password: "n3w-secret-456",
        confirm_new_password: "different-secret",
      }),
    );

    expect(result).toEqual({ ok: false, error: "new passwords do not match" });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("changePassword submit", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the three fields as JSON to the account endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ other_devices_signed_out: true }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await changePassword(
      formWith({
        current_password: "s3cret123",
        new_password: "n3w-secret-456",
        confirm_new_password: "n3w-secret-456",
      }),
    );

    expect(fetchMock).toHaveBeenCalledWith("/api/account/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: "s3cret123",
        new_password: "n3w-secret-456",
        confirm_new_password: "n3w-secret-456",
      }),
    });
  });

  it("reports the other-device outcome on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ other_devices_signed_out: true }), { status: 200 }),
      ),
    );
    expect(
      await changePassword(
        formWith({
          current_password: "s3cret123",
          new_password: "n3w-secret-456",
          confirm_new_password: "n3w-secret-456",
        }),
      ),
    ).toEqual({ ok: true, otherDevicesSignedOut: true });
  });

  it("surfaces the wrong-current detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "wrong current password" }), { status: 401 }),
      ),
    );
    expect(
      await changePassword(
        formWith({
          current_password: "nope",
          new_password: "n3w-secret-456",
          confirm_new_password: "n3w-secret-456",
        }),
      ),
    ).toEqual({ ok: false, error: "wrong current password" });
  });

  it("surfaces the weak-password detail verbatim", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "weak password" }), { status: 422 }),
      ),
    );
    expect(
      await changePassword(
        formWith({
          current_password: "s3cret123",
          new_password: "short",
          confirm_new_password: "short",
        }),
      ),
    ).toEqual({ ok: false, error: "weak password" });
  });

  it("falls back to the status when the body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("nope", { status: 502 })));
    expect(
      await changePassword(
        formWith({
          current_password: "s3cret123",
          new_password: "n3w-secret-456",
          confirm_new_password: "n3w-secret-456",
        }),
      ),
    ).toEqual({ ok: false, error: "request failed (502)" });
  });

  it("maps a thrown fetch to a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(
      await changePassword(
        formWith({
          current_password: "s3cret123",
          new_password: "n3w-secret-456",
          confirm_new_password: "n3w-secret-456",
        }),
      ),
    ).toEqual({ ok: false, error: "network error" });
  });
});

describe("outcome note", () => {
  it("tells the user other devices were signed out", () => {
    expect(outcomeNote(true)).toContain("other devices were signed out");
  });

  it("tells the user other devices stay signed in", () => {
    expect(outcomeNote(false)).toContain("other devices stay signed in");
  });
});
