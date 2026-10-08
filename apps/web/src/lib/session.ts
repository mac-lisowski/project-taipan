import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { NextResponse } from "next/server";
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
export const requireAccount = cache(async (): Promise<Me> => {
  const token = await getSessionToken();
  const decision = await resolveAccount(token);
  if ("redirect" in decision) {
    redirect(decision.redirect);
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
