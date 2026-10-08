import { submitAuth, type AuthResult } from "./auth-submit";
import type { SwitchRead } from "./system-settings";

// Single source for the post-activation destination. Login, activation,
// and reset all land on the dashboard so the flows agree.
export const REGISTER_LANDING = "/dashboard";

// Step one: request an activation mail. The API answers the same for
// known and unknown mail, so ok only means "watch the inbox".
export async function submitRegister(email: string): Promise<AuthResult> {
  const form = new FormData();
  form.set("email", email);
  return submitAuth("/api/auth/register", form);
}

// Step two: the mailed link. The BFF re-emits the session cookie on 204;
// the API field is "password" and upstream detail surfaces verbatim.
export async function submitActivation(
  token: string,
  password: string,
): Promise<AuthResult> {
  const form = new FormData();
  form.set("token", token);
  form.set("password", password);
  return submitAuth("/api/auth/activate", form);
}

// Gate for the sign up door: the switch read is the only source of
// truth; unknown degrades to a neutral note, never a fake 404. A token
// bypasses the off check so a mailed link still works after a close.
export type RegisterGate =
  | { view: "not-found" }
  | { view: "error"; message: string }
  | { view: "email-form" }
  | { view: "set-password"; token: string };

export function chooseRegisterGate(
  read: SwitchRead,
  token?: string,
): RegisterGate {
  if (!read.ok) return { view: "error", message: read.error };
  if (token) return { view: "set-password", token };
  if (!read.data.enabled) return { view: "not-found" };
  return { view: "email-form" };
}

// The sign up link shows only on an open switch; off and unknown hide it.
export function showSignUpLink(read: SwitchRead): boolean {
  return read.ok && read.data.enabled;
}
