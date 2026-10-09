import { NextResponse, type NextRequest } from "next/server";

import { NEXT_HEADER } from "@/lib/return-path";

// Stamps the attempted private URL (path plus query) on a request header
// so the layout's auth guard can build a `?next=` login link. The proxy
// never decides auth itself: session.ts stays the authoritative check.
export function proxy(request: NextRequest): NextResponse {
  const headers = new Headers(request.headers);
  headers.set(
    NEXT_HEADER,
    request.nextUrl.pathname + request.nextUrl.search,
  );
  return NextResponse.next({ request: { headers } });
}

// Only the (private) routes need a return path; the guard cannot fire
// anywhere else.
export const config = {
  matcher: [
    "/chat",
    "/dashboard",
    "/users",
    "/account",
    "/settings",
    "/system/:path*",
  ],
};
