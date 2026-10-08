import { submitAuth, type AuthResult } from "./auth-submit";

// Single source for the post-reset destination. Login, activation, and
// reset all land on the dashboard so the flows agree.
export const RESET_LANDING = "/dashboard";

// Reset through the shared auth seam. The body carries the API's exact
// field names ({"token", "new_password"}); upstream detail is surfaced
// verbatim, so 400 and 422 differ only by the API's message.
export async function submitReset(
  token: string,
  newPassword: string,
): Promise<AuthResult> {
  const form = new FormData();
  form.set("token", token);
  form.set("new_password", newPassword);
  return submitAuth("/api/auth/reset", form);
}
