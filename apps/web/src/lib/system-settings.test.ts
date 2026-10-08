import { afterEach, describe, expect, it, vi } from "vitest";
import {
  loadRegistrationSwitch,
  reduceSwitchView,
  setRegistrationSwitch,
  switchValue,
} from "./system-settings";

const OWNER_DENIED = JSON.stringify({ detail: "system owner role required" });

describe("loadRegistrationSwitch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETs the same-origin path and maps the body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ enabled: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadRegistrationSwitch();

    expect(fetchMock).toHaveBeenCalledWith("/api/system/registration");
    expect(result).toEqual({ ok: true, data: { enabled: true } });
  });

  it("maps an off switch", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ enabled: false }), { status: 200 }),
      ),
    );
    expect(await loadRegistrationSwitch()).toEqual({ ok: true, data: { enabled: false } });
  });

  it("coerces a non-boolean wire value to off", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ enabled: "true" }), { status: 200 }),
      ),
    );
    expect(await loadRegistrationSwitch()).toEqual({ ok: true, data: { enabled: false } });
  });

  it("maps an absent body to an off switch", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    expect(await loadRegistrationSwitch()).toEqual({ ok: true, data: { enabled: false } });
  });

  it("surfaces the upstream detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(OWNER_DENIED, { status: 403 })),
    );
    expect(await loadRegistrationSwitch()).toEqual({
      ok: false,
      error: "system owner role required",
    });
  });

  it("maps a thrown fetch to a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await loadRegistrationSwitch()).toEqual({
      ok: false,
      error: "network error",
    });
  });
});

describe("setRegistrationSwitch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("PUTs the new value as JSON to the same-origin path and maps the 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await setRegistrationSwitch(true);

    expect(fetchMock).toHaveBeenCalledWith("/api/system/registration", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: true }),
    });
    expect(result).toEqual({ ok: true, data: null });
  });

  it("carries the API error verbatim on denial", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(OWNER_DENIED, { status: 403 })),
    );
    expect(await setRegistrationSwitch(false)).toEqual({
      ok: false,
      error: "system owner role required",
    });
  });
});

describe("reduceSwitchView", () => {
  it("shows the loaded value as ready", () => {
    const view = reduceSwitchView(
      { state: "loading" },
      { type: "loaded", result: { ok: true, data: { enabled: false } } },
    );
    expect(view).toEqual({ state: "ready", enabled: false });
  });

  it("carries a load failure into the error state", () => {
    const view = reduceSwitchView(
      { state: "loading" },
      { type: "loaded", result: { ok: false, error: "network error" } },
    );
    expect(view).toEqual({ state: "error", message: "network error", enabled: null });
  });

  it("is pending while the save is in flight", () => {
    const view = reduceSwitchView(
      { state: "ready", enabled: true },
      { type: "save_started", enabled: false },
    );
    expect(view).toEqual({ state: "saving", enabled: false });
  });

  it("is saved after a 204", () => {
    const view = reduceSwitchView(
      { state: "saving", enabled: false },
      { type: "save_finished", result: { ok: true, data: null } },
    );
    expect(view).toEqual({ state: "saved", enabled: false });
  });

  it("keeps the view when a save lands outside saving", () => {
    const view = reduceSwitchView(
      { state: "ready", enabled: true },
      { type: "save_finished", result: { ok: true, data: null } },
    );
    expect(view).toEqual({ state: "ready", enabled: true });
  });

  it("reverts to the pre-flip value when the save fails", () => {
    const view = reduceSwitchView(
      { state: "saving", enabled: false },
      {
        type: "save_finished",
        result: { ok: false, error: "system owner role required" },
      },
    );
    expect(view).toEqual({
      state: "error",
      message: "system owner role required",
      enabled: true,
    });
  });
});

describe("switchValue", () => {
  it("reads the last known value for the toggle", () => {
    expect(switchValue({ state: "loading" })).toBeNull();
    expect(switchValue({ state: "ready", enabled: true })).toBe(true);
    expect(switchValue({ state: "error", message: "x", enabled: false })).toBe(false);
  });
});
