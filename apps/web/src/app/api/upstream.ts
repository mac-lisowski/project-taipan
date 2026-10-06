import { apiInternalUrl } from "./env";

export type Me = {
  id: number;
  email: string;
  tenant_id: string;
  roles: string[];
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
