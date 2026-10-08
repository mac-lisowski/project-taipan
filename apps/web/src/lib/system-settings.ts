// Web side of the registration switch: same-origin /api calls through the
// BFF plus a small view-state machine. The endpoint result is the only
// source of switch state; the client never decides a value on its own.

import { getJson, putJson, type ApiResult } from "./api-result";

export const REGISTRATION_PATH = "/api/system/registration";

export type SwitchRead = ApiResult<{ enabled: boolean }>;

export type SetResult = ApiResult<null>;

export async function loadRegistrationSwitch(): Promise<SwitchRead> {
  const res = await getJson<{ enabled?: unknown }>(REGISTRATION_PATH);
  if (!res.ok) return res;
  // The wire is untyped; only the boolean true opens the switch.
  return { ok: true, data: { enabled: res.data?.enabled === true } };
}

export function setRegistrationSwitch(enabled: boolean): Promise<SetResult> {
  return putJson<null>(REGISTRATION_PATH, { enabled });
}

export type RegistrationSwitchView =
  | { state: "loading" }
  | { state: "ready"; enabled: boolean }
  | { state: "saving"; enabled: boolean }
  | { state: "saved"; enabled: boolean }
  | { state: "error"; message: string; enabled: boolean | null };

export type SwitchAction =
  | { type: "loaded"; result: SwitchRead }
  | { type: "save_started"; enabled: boolean }
  | { type: "save_finished"; result: SetResult };

export function reduceSwitchView(
  view: RegistrationSwitchView,
  action: SwitchAction,
): RegistrationSwitchView {
  switch (action.type) {
    case "loaded":
      return action.result.ok
        ? { state: "ready", enabled: action.result.data.enabled }
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
