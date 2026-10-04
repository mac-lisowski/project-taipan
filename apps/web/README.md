# apps/web

Next.js (App Router) frontend. It is the BFF for the browser: pages
are server-rendered and `src/app/api/[...path]/route.ts` proxies
`/api/*` to FastAPI, forwarding the session cookie. The browser never
calls FastAPI directly.

```bash
pnpm install        # one-time, or after lockfile changes
pnpm dev            # dev server on :3000; needs `uv run api` on :8000
pnpm build          # production build (standalone output)
pnpm lint           # eslint
pnpm exec tsc --noEmit   # typecheck
```

Env: copy `.env.example` to `.env.local` to override. Only
`API_INTERNAL_URL` exists and it is server-only.

Deploy: `Dockerfile` builds a standalone image; context is this dir.
