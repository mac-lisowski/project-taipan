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
  | {
      state: "ready";
      users: UserRow[];
      query: string;
      status: StatusFilter;
      page: number;
    }
  | { state: "error"; message: string };

export type StatusFilter = "all" | "active" | "inactive";

export type UsersAction =
  | { type: "loaded"; result: UsersLoadResult }
  | { type: "query_changed"; query: string }
  | { type: "status_changed"; status: StatusFilter };

export function reduceUsersView(
  view: UsersView,
  action: UsersAction,
): UsersView {
  switch (action.type) {
    case "loaded":
      return action.result.ok
        ? {
            state: "ready",
            users: action.result.users,
            query: "",
            status: "all",
            page: 1,
          }
        : { state: "error", message: action.result.error };
    case "query_changed":
      // Any control change re-opens the list at page one.
      return view.state === "ready"
        ? { ...view, query: action.query, page: 1 }
        : view;
    case "status_changed":
      return view.state === "ready"
        ? { ...view, status: action.status, page: 1 }
        : view;
  }
}

export function searchUsers(users: UserRow[], query: string): UserRow[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return users;
  return users.filter((user) => user.email.toLowerCase().includes(needle));
}

export function filterUsersByStatus(
  users: UserRow[],
  status: StatusFilter,
): UserRow[] {
  if (status === "all") return users;
  return users.filter((user) =>
    status === "active" ? user.is_active : !user.is_active,
  );
}

export function applyUsersQuery(
  users: UserRow[],
  query: string,
  status: StatusFilter,
): UserRow[] {
  return filterUsersByStatus(searchUsers(users, query), status);
}

export function formatDate(iso: string): string {
  return iso.slice(0, 10);
}
