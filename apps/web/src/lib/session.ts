import { cache } from "react";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import type { NextResponse } from "next/server";
import { NEXT_HEADER } from "@/lib/return-path";
import { resolveAccount, revokeSession, type Me } from "../app/api/upstream";

export const SESSION_COOKIE_NAME = "session";

export function sessionCookieHeader(token: string): string {
  return `${SESSION_COOKIE_NAME}=${token}`;
}

export async function getSessionToken(): Promise<string | undefined> {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE_NAME)?.value;
}

export async function hasSession(): Promise<boolean> {
  return (await getSessionToken()) !== undefined;
}

export function clearSessionCookie(response: NextResponse): void {
  response.cookies.set(SESSION_COOKIE_NAME, "", { maxAge: 0, path: "/" });
}

// Guard protected server components by redirecting unauthenticated visitors.
// The proxy stamps the attempted URL on NEXT_HEADER so the login page can
// send the user back (pane param included); without it the redirect stays bare.
export const requireAccount = cache(async (): Promise<Me> => {
  const token = await getSessionToken();
  const decision = await resolveAccount(token);
  if ("redirect" in decision) {
    const next = (await headers()).get(NEXT_HEADER);
    redirect(
      next === null
        ? decision.redirect
        : `${decision.redirect}?next=${encodeURIComponent(next)}`,
    );
  }
  return decision.me;
});


// Steer authenticated visitors away from public auth forms; chat is home.
export async function redirectIfAuthenticated(to = "/chat"): Promise<void> {
  if (await hasSession()) {
    redirect(to);
  }
}

// Combine remote revocation and local cookie clearance for clean logout.
export async function terminateSession(response: NextResponse): Promise<void> {
  const token = await getSessionToken();
  if (token !== undefined) {
    await revokeSession(token);
  }
  clearSessionCookie(response);
}
