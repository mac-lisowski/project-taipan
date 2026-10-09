// Pure layer for the server-rendered users list: URL params, payload guard, page math.

export type UserRow = {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type UsersPagePayload = {
  items: UserRow[];
  total: number;
  total_all: number;
  page: number;
  page_size: number;
};

export type UsersRead = { ok: true; data: UsersPagePayload } | { ok: false; error: string };

// Filters plus the detail id: the URL params are the only source.
export type UsersFilters = {
  q: string;
  status: StatusFilter;
  page: number;
  pageSize: PageSize;
  user: number | null;
};

export type UsersBoot = { filters: UsersFilters; result: UsersRead };

export type StatusFilter = "all" | "active" | "inactive";

export type PageSize = 10 | 25 | 50;

export const PAGE_SIZES: PageSize[] = [10, 25, 50];

export const DEFAULT_PAGE_SIZE: PageSize = 10;

const Q_MAX = 200;

const STATUSES: readonly string[] = ["all", "active", "inactive"];

function one(params: Record<string, string | string[] | undefined>, key: string): string {
  const value = params[key];
  return typeof value === "string" ? value : "";
}

// Shared links carry untrusted values, so every field falls back to
// its default instead of surfacing an API 422.
export function parseUsersFilters(
  params: Record<string, string | string[] | undefined>,
): UsersFilters {
  const page = Number.parseInt(one(params, "page"), 10);
  const size = Number.parseInt(one(params, "size"), 10);
  const user = Number.parseInt(one(params, "user"), 10);
  const status = one(params, "status");
  return {
    q: one(params, "q").slice(0, Q_MAX),
    status: STATUSES.includes(status) ? (status as StatusFilter) : "all",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    pageSize: isPageSize(size) ? size : DEFAULT_PAGE_SIZE,
    user: Number.isInteger(user) && user >= 1 ? user : null,
  };
}

function isPageSize(size: number): size is PageSize {
  return (PAGE_SIZES as readonly number[]).includes(size);
}

// Defaults stay out of the URL, so a clean /users is page one.
export function filtersToParams(filters: UsersFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim() !== "") params.set("q", filters.q);
  if (filters.status !== "all") params.set("status", filters.status);
  if (filters.page !== 1) params.set("page", String(filters.page));
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) {
    params.set("size", String(filters.pageSize));
  }
  if (filters.user !== null) params.set("user", String(filters.user));
  return params;
}

export function usersPath(filters: UsersFilters): string {
  const query = filtersToParams(filters).toString();
  return query === "" ? "/users" : `/users?${query}`;
}

// The server guards the body shape before render; a wrong shape is an
// error state, never a crashed table.
export function guardUsersPage(body: unknown): UsersPagePayload | null {
  if (typeof body !== "object" || body === null) return null;
  const page = body as Record<string, unknown>;
  const items = page.items;
  if (!Array.isArray(items)) return null;
  const rows: UserRow[] = [];
  for (const item of items) {
    if (typeof item !== "object" || item === null) return null;
    const row = item as Record<string, unknown>;
    if (
      typeof row.id !== "number" ||
      typeof row.email !== "string" ||
      typeof row.is_active !== "boolean" ||
      typeof row.created_at !== "string"
    ) {
      return null;
    }
    rows.push({ id: row.id, email: row.email, is_active: row.is_active, created_at: row.created_at });
  }
  if (
    typeof page.total !== "number" ||
    typeof page.total_all !== "number" ||
    typeof page.page !== "number" ||
    typeof page.page_size !== "number" ||
    page.page < 1
  ) {
    return null;
  }
  return {
    items: rows,
    total: page.total,
    total_all: page.total_all,
    page: page.page,
    page_size: page.page_size,
  };
}

export function pageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

// Tests hold the exact strings; change copy and tests together.
export const USERS_COPY = {
  error: "err",
  empty: "no users match",
  retry: "retry",
} as const;

export function countLine(total: number, totalAll: number): string {
  return `${total} of ${totalAll} users`;
}

export function formatDate(iso: string): string {
  return iso.slice(0, 10);
}
