// Web side of the users list: same-origin /api call through the BFF
// plus pure helpers for search, filter, and paging. The endpoint
// result is the only source of list state.

import { errorDetailOf } from "./api-detail";

export const USERS_PATH = "/api/users";

export type UserRow = {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type UsersLoadResult =
  | { ok: true; users: UserRow[] }
  | { ok: false; error: string };

export async function loadUsers(): Promise<UsersLoadResult> {
  try {
    const res = await fetch(USERS_PATH);
    if (!res.ok) return { ok: false, error: await errorDetailOf(res) };
    const body = (await res.json().catch(() => null)) as UserRow[] | null;
    if (!Array.isArray(body)) return { ok: false, error: "unexpected users body" };
    return { ok: true, users: body };
  } catch {
    return { ok: false, error: "network error" };
  }
}

export type UsersView =
  | { state: "loading" }
  | { state: "ready"; users: UserRow[] }
  | { state: "error"; message: string };

export type UsersAction = { type: "loaded"; result: UsersLoadResult };

export function reduceUsersView(
  view: UsersView,
  action: UsersAction,
): UsersView {
  return action.result.ok
    ? { state: "ready", users: action.result.users }
    : { state: "error", message: action.result.error };
}

export function formatDate(iso: string): string {
  return iso.slice(0, 10);
}
