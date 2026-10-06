# apps/web

Next.js (App Router) frontend. It is the BFF for the browser: pages
are server-rendered and `src/app/api/[...path]/route.ts` proxies
`/api/*` to FastAPI, forwarding the session cookie. The browser never
calls FastAPI directly.

It serves auth pages (`/`, `/register`, `/forgot`) and renders the
repo `docs/` markdown at `/docs`.

```bash
pnpm install        # one-time, or after lockfile changes
pnpm dev            # dev server on :3000; needs `uv run api` on :8000
pnpm build          # production build (standalone output)
pnpm test           # vitest unit tests
pnpm lint           # eslint
pnpm exec next typegen && pnpm exec tsc --noEmit   # typecheck (typegen first on clean checkout)
```

Env: copy `.env.example` to `.env.local` to override.

| Var | Purpose |
|---|---|
| `API_INTERNAL_URL` | FastAPI origin for the `/api/*` proxy. Server-only; required in production. |
| `PUBLIC_ORIGIN` | Browser-facing origin for rewriting upstream redirects. Required in production. |
| `DOCS_DIR` | Override for where the docs site reads markdown. Optional; the Dockerfile sets it. |

Deploy: `scripts/docker-build.sh web` from the
repo root (context is the root, same as `apps/api/Dockerfile`).
