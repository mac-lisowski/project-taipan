# Web is a Next.js BFF

Option B.1: the browser only reaches Next, the catch-all in
`src/app/api/[...path]/route.ts` forwards to FastAPI. FastAPI owns
sessions + Redis; web has no REDIS_URL, only API_INTERNAL_URL
(server-only, never NEXT_PUBLIC_).
