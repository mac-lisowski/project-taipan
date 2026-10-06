import { NextResponse } from "next/server";
import { terminateSession } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Logout is a mutation, so only POST answers: a GET fired on <Link> prefetch.
export async function POST(): Promise<Response> {
  const res = new NextResponse(null, { status: 204 });
  await terminateSession(res);
  return res;
}
