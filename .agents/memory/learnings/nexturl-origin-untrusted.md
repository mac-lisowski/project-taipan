# nextUrl.origin is client-controlled

NextRequest.nextUrl.origin derives scheme+host from client-sent
x-forwarded-proto/host headers - it is NOT trusted input. For a
proxy, build the fallback origin as http + Host and require an
explicit PUBLIC_ORIGIN env in production.
