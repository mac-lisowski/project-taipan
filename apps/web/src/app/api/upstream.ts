import { apiInternalUrl } from "./env";
import type { ThreadSeed } from "@/lib/chat-config";
import {
  guardUsersPage,
  usersApiQuery,
  type UsersFilters,
  type UsersRead,
} from "@/lib/users-list";
import type { SwitchRead } from "../../lib/system-settings";

export type Me = {
  id: number;
  email: string;
  tenant_id: string;
  roles: string[];
  system_roles: string[];
};

export type AccountDecision = { redirect: "/" } | { me: Me };

export type LandingDecision =
  | { view: "setup" }
  | { view: "login" }
  | { view: "error"; error: string };

// Probe mapping for server render: failure is an error, never a wrong form.
export async function resolveLanding(): Promise<LandingDecision> {
  let res: Response;
  try {
    res = await fetch(`${apiInternalUrl()}/api/setup`, { cache: "no-store" });
  } catch {
    return { view: "error", error: "setup probe failed" };
  }
  if (!res.ok) return { view: "error", error: `setup probe failed (${res.status})` };
  const data: unknown = await res.json().catch(() => null);
  if (
    typeof data !== "object" ||
    data === null ||
    typeof (data as { needs_setup?: unknown }).needs_setup !== "boolean"
  ) {
    return { view: "error", error: "setup probe gave an unexpected answer" };
  }
  return { view: (data as { needs_setup: boolean }).needs_setup ? "setup" : "login" };
}

// Server-side read of the public registration switch: no-store so a
// flip to off closes the sign up door on the very next render.
export async function resolveRegistrationSwitch(): Promise<SwitchRead> {
  let res: Response;
  try {
    res = await fetch(`${apiInternalUrl()}/api/system/registration`, {
      cache: "no-store",
    });
  } catch {
    return { ok: false, error: "registration switch read failed" };
  }
  if (!res.ok) {
    return { ok: false, error: `registration switch read failed (${res.status})` };
  }
  const data: unknown = await res.json().catch(() => null);
  if (
    typeof data !== "object" ||
    data === null ||
    typeof (data as { enabled?: unknown }).enabled !== "boolean"
  ) {
    return { ok: false, error: "registration switch gave an unexpected answer" };
  }
  return { ok: true, data: { enabled: (data as { enabled: boolean }).enabled } };
}

// Best-effort revoke: never throws, so logout works with the API down.
export async function revokeSession(session: string): Promise<void> {
  try {
    await fetch(`${apiInternalUrl()}/api/auth/logout`, {
      method: "POST",
      headers: { Cookie: `session=${session}` },
    });
  } catch {
    // Logged out locally regardless; the server row expires on its own.
  }
}

// One users page per render; a wrong body becomes an error read, never a crash.
export async function resolveUsersPage(
  session: string | undefined,
  filters: UsersFilters,
): Promise<UsersRead> {
  if (!session) return { ok: false, error: "no session" };
  // filtersToParams owns default omission; names map to the API's and user drops.
  const qs = usersApiQuery(filters).toString();
  const url = qs === "" ? `${apiInternalUrl()}/api/users` : `${apiInternalUrl()}/api/users?${qs}`;
  let res: Response;
  try {
    res = await fetch(url, {
      headers: { Cookie: `session=${session}` },
      cache: "no-store",
    });
  } catch {
    return { ok: false, error: "users list failed" };
  }
  if (!res.ok) return { ok: false, error: await errorDetail(res, "users list failed") };
  const body: unknown = await res.json().catch(() => null);
  const page = guardUsersPage(body);
  if (page === null) return { ok: false, error: "unexpected users page body" };
  return { ok: true, data: page };
}

// First threads cursor page; any failure answers null and the client fetch carries on.
export async function resolveThreadsSeed(
  session: string | undefined,
): Promise<ThreadSeed | null> {
  if (!session) return null;
  let res: Response;
  try {
    res = await fetch(`${apiInternalUrl()}/api/threads/get`, {
      headers: { Cookie: `session=${session}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  if (!res.ok) return null;
  const body: unknown = await res.json().catch(() => null);
  if (typeof body !== "object" || body === null) return null;
  const threads = (body as { threads?: unknown }).threads;
  if (!Array.isArray(threads)) return null;
  const cursor = (body as { nextCursor?: unknown }).nextCursor;
  return {
    threads: threads as ThreadSeed["threads"],
    nextCursor: typeof cursor === "string" ? cursor : undefined,
  };
}

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const body: unknown = await res.json().catch(() => null);
  if (
    typeof body === "object" &&
    body !== null &&
    typeof (body as { detail?: unknown }).detail === "string"
  ) {
    return (body as { detail: string }).detail;
  }
  return `${fallback} (${res.status})`;
}

// Server-only account lookup: the inbound session cookie goes out as
// the Cookie header with no-store. No cookie or a 401 means landing;
// any other upstream failure throws instead of looping redirects.
export async function resolveAccount(
  session: string | undefined,
): Promise<AccountDecision> {
  if (!session) return { redirect: "/" };
  const res = await fetch(`${apiInternalUrl()}/api/auth/me`, {
    headers: { Cookie: `session=${session}` },
    cache: "no-store",
  });
  if (res.status === 401) return { redirect: "/" };
  if (!res.ok) throw new Error(`account lookup failed (${res.status})`);
  return { me: (await res.json()) as Me };
}
