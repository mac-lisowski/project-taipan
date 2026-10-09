// Browser-side users page fetch for the pane adapter. The request goes
// through the BFF (/api/users on the same origin), so the session cookie
// rides along and the API's owner gate applies exactly as it does for
// the server-rendered page. fetchImpl is injectable for tests.

import {
  guardUsersPage,
  usersApiQuery,
  type UsersFilters,
  type UsersRead,
} from "@/lib/users-list";

export async function fetchUsersPage(
  filters: UsersFilters,
  fetchImpl: typeof fetch = fetch,
): Promise<UsersRead> {
  const qs = usersApiQuery(filters).toString();
  const url = qs === "" ? "/api/users" : `/api/users?${qs}`;
  let res: Response;
  try {
    res = await fetchImpl(url, { cache: "no-store" });
  } catch {
    return { ok: false, error: "users list failed" };
  }
  if (!res.ok) return { ok: false, error: `users list failed (${res.status})` };
  const body: unknown = await res.json().catch(() => null);
  const page = guardUsersPage(body);
  if (page === null) return { ok: false, error: "unexpected users page body" };
  return { ok: true, data: page };
}
