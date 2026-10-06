import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";
import { publicOrigin, revokeSession } from "@/app/api/upstream";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Logout is a navigation, not a background request.
export async function GET(req: NextRequest): Promise<Response> {
  const session = (await cookies()).get("session")?.value;
  if (session !== undefined) await revokeSession(session);
  const forwardedHost = req.headers.get("x-forwarded-host");
  const host = forwardedHost ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "http";
  // Self redirect only, never an upstream address.
  const origin = publicOrigin() ?? (host !== null ? `${proto}://${host}` : new URL(req.url).origin);
  const res = NextResponse.redirect(new URL("/", origin));
  res.cookies.set("session", "", { maxAge: 0, path: "/" });
  return res;
}
