// Web side of the registration switch: same-origin /api calls through the
// BFF plus a small view-state machine. The endpoint result is the only
// source of switch state; the client never decides a value on its own.

import { errorDetailOf } from "./api-detail";

export const REGISTRATION_PATH = "/api/system/registration";

export type LoadResult =
  | { ok: true; enabled: boolean }
  | { ok: false; error: string };

export type SetResult = { ok: true } | { ok: false; error: string };

export async function loadRegistrationSwitch(): Promise<LoadResult> {
  try {
    const res = await fetch(REGISTRATION_PATH);
    if (!res.ok) return { ok: false, error: await errorDetailOf(res) };
    const body = (await res.json().catch(() => null)) as {
      enabled?: unknown;
    } | null;
    return { ok: true, enabled: body?.enabled === true };
  } catch {
    return { ok: false, error: "network error" };
  }
}

export async function setRegistrationSwitch(
  enabled: boolean,
): Promise<SetResult> {
  try {
    const res = await fetch(REGISTRATION_PATH, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (!res.ok) return { ok: false, error: await errorDetailOf(res) };
    return { ok: true };
  } catch {
    return { ok: false, error: "network error" };
  }
}

export type RegistrationSwitchView =
  | { state: "loading" }
  | { state: "ready"; enabled: boolean }
  | { state: "saving"; enabled: boolean }
  | { state: "saved"; enabled: boolean }
  | { state: "error"; message: string; enabled: boolean | null };

export type SwitchAction =
  | { type: "loaded"; result: LoadResult }
  | { type: "save_started"; enabled: boolean }
  | { type: "save_finished"; result: SetResult };

export function reduceSwitchView(
  view: RegistrationSwitchView,
  action: SwitchAction,
): RegistrationSwitchView {
  switch (action.type) {
    case "loaded":
      return action.result.ok
        ? { state: "ready", enabled: action.result.enabled }
        : { state: "error", message: action.result.error, enabled: null };
    case "save_started":
      return { state: "saving", enabled: action.enabled };
    case "save_finished":
      // Only a save in flight can land; stale finishes keep the old view.
      if (view.state !== "saving") return view;
      return action.result.ok
        ? { state: "saved", enabled: view.enabled }
        : {
            state: "error",
            message: action.result.error,
            // A failed save reverts to the pre-flip value; the server kept it.
            enabled: !view.enabled,
          };
  }
}

// The value the toggle paints; null means nothing to show yet.
export function switchValue(view: RegistrationSwitchView): boolean | null {
  if (view.state === "loading") return null;
  return view.enabled;
}
