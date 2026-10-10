# BFF proxy strips Content-Length both directions

- `apps/web/src/lib/upstream-proxy.ts`: request headers drop
  `content-length` (undici recomputes); `req.body` streams with
  `duplex:"half"`. Upstream sees chunked TE.
- `RESPONSE_REWRITE` drops `content-length` on responses too.
- Consequences: request-size bounds must count ASGI receive bytes,
  not read the header. Downloads reach the browser chunked whatever
  the API pinned.
