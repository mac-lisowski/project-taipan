# Resolve session once per request

Cache the middleware resolve on `request.state`, bound to the cookie
token. Authz reuses it on token match, resolves fresh otherwise.
Fallback keeps middleware-less authz tests and bare requests working.
Token binding keeps a stale value from authorizing another token.
Same-token staleness window shrinks to zero: both readers share one
read, so a revocation landing mid-request can no longer split them.
Residual risk is one request granting what a microsecond-later read
would deny; accepted because the window is the request itself.
