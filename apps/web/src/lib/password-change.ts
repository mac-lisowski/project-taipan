import type { ApiResult } from "./api-result";
import { submitAuth } from "./auth-submit";

// Mirror of the API's one shared password rule (credentials.ensure_acceptable):
// display only, the API stays the only gate.
export const MIN_PASSWORD_LENGTH = 8;
export const PASSWORD_RULES = `at least ${MIN_PASSWORD_LENGTH} characters`;

// Display-only state for the strength bar; it never blocks submit.
export function ruleMet(next: string): boolean {
  return next.length >= MIN_PASSWORD_LENGTH;
}

export function mismatchError(next: string, confirm: string): string | null {
  return next === confirm ? null : "new passwords do not match";
}

export function outcomeNote(otherDevicesSignedOut: boolean): string {
  return otherDevicesSignedOut
    ? "password changed. this device stays signed in. other devices were signed out."
    : "password changed. this device stays signed in. other devices stay signed in.";
}

export type ChangePasswordResult = ApiResult<boolean>;

// Double-entry guard, then the shared submit path. The outcome rides the
// shared data channel; the error channel is submitAuth's verbatim.
export async function changePassword(formData: FormData): Promise<ChangePasswordResult> {
  const value = (name: string) => String(formData.get(name) ?? "");
  const mismatch = mismatchError(value("new_password"), value("confirm_new_password"));
  if (mismatch !== null) return { ok: false, error: mismatch };
  const result = await submitAuth("/api/account/password", formData);
  if (!result.ok) return result;
  const body = (result.data ?? {}) as { other_devices_signed_out?: unknown };
  return { ok: true, data: body.other_devices_signed_out === true };
}
