import { NextResponse, type NextRequest } from "next/server";
import { publicOrigin } from "@/app/api/env";
import { resolveTrustedOrigin } from "@/lib/origin";
import { terminateSession } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Logout is a navigation, not a background request.
export async function GET(req: NextRequest): Promise<Response> {
  const origin = resolveTrustedOrigin(req, publicOrigin());
  const res = NextResponse.redirect(new URL("/", origin));
  await terminateSession(res);
  return res;
}

