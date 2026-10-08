// The endpoint result is the only source of users list state.

import { getJson, type ApiResult } from "./api-result";

export const USERS_PATH = "/api/users";

export type UserRow = {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type UsersLoadResult = ApiResult<UserRow[]>;

export async function loadUsers(): Promise<UsersLoadResult> {
  const res = await getJson<unknown>(USERS_PATH);
  // The array guard stays here so the reducer only ever sees typed rows.
  if (!res.ok) return res;
  if (!Array.isArray(res.data)) {
    return { ok: false, error: "unexpected users body" };
  }
  return { ok: true, data: res.data };
}

export type StatusFilter = "all" | "active" | "inactive";

export type PageSize = 10 | 25 | 50;

export const PAGE_SIZES: PageSize[] = [10, 25, 50];

export type UsersAction =
  | { type: "loaded"; result: UsersLoadResult }
  | { type: "query_changed"; query: string }
  | { type: "status_changed"; status: StatusFilter }
  | { type: "page_changed"; page: number }
  | { type: "page_size_changed"; pageSize: PageSize }
  | { type: "retry" };

export type UsersView =
  | { state: "loading" }
  | {
      state: "ready";
      users: UserRow[];
      query: string;
      status: StatusFilter;
      page: number;
      pageSize: PageSize;
    }
  | { state: "error"; message: string };

export function reduceUsersView(
  view: UsersView,
  action: UsersAction,
): UsersView {
  switch (action.type) {
    case "loaded":
      return action.result.ok
        ? {
            state: "ready",
            users: action.result.data,
            query: "",
            status: "all",
            page: 1,
            pageSize: 10,
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
    case "page_changed":
      return view.state === "ready"
        ? {
            ...view,
            // The pager clamps to the last page of the filtered list.
            page: clampPage(
              action.page,
              applyUsersQuery(view.users, view.query, view.status).length,
              view.pageSize,
            ),
          }
        : view;
    case "page_size_changed":
      return view.state === "ready"
        ? { ...view, pageSize: action.pageSize, page: 1 }
        : view;
    case "retry":
      return { state: "loading" };
  }
}

export function pageCount(itemCount: number, pageSize: number): number {
  return Math.max(1, Math.ceil(itemCount / pageSize));
}

export function clampPage(
  page: number,
  itemCount: number,
  pageSize: number,
): number {
  return Math.min(Math.max(1, page), pageCount(itemCount, pageSize));
}

export function pageSlice(
  users: UserRow[],
  page: number,
  pageSize: number,
): UserRow[] {
  const start = (clampPage(page, users.length, pageSize) - 1) * pageSize;
  return users.slice(start, start + pageSize);
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

// Screen copy pinned by the spec; tests hold the exact strings.
export const USERS_COPY = {
  loading: "loading…",
  empty: "no users match",
  retry: "retry",
} as const;

export function countLine(filtered: number, total: number): string {
  return `${filtered} of ${total} users`;
}
