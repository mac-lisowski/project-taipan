import { NextResponse, type NextRequest } from "next/server";
import { publicOrigin, revokeSession } from "@/app/api/upstream";
import { clearSessionCookie, getSessionToken } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Logout is a navigation, not a background request.
export async function GET(req: NextRequest): Promise<Response> {
  const session = await getSessionToken();
  if (session !== undefined) await revokeSession(session);
  const forwardedHost = req.headers.get("x-forwarded-host");
  const host = forwardedHost ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "http";
  // Self redirect only, never an upstream address.
  const origin = publicOrigin() ?? (host !== null ? `${proto}://${host}` : new URL(req.url).origin);
  const res = NextResponse.redirect(new URL("/", origin));
  clearSessionCookie(res);
  return res;
}
