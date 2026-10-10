# BFF proxy aborts upstream calls at 30 s

- `apps/web/src/lib/upstream-proxy.ts` `DEFAULT_TIMEOUT_MS = 30_000`
  on `AbortSignal.timeout` for every proxied call.
- Any endpoint whose transfer can exceed 30 s (file up/download)
  needs a larger `timeoutMs` on a dedicated BFF route, or a byte cap
  that fits inside the budget.
