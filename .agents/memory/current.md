# Current state

- Last updated: 2026-10-05
- Branch feat/bff-proxy-module @ a62c277: bff-proxy-module spec done
  (tickets 01 + 02, reports in .scratch/bff-proxy-module/issues/).
  All commits local; nothing pushed.
- Workflow: implement-spec runs ticket by ticket; no push, no PR
  unless the user asks; review-stamp before every commit.
- Next step: merge feat/bff-proxy-module to dev (user says when).
  Then auth/session layer: FastAPI owns sessions in Redis via
  API_REDIS_URL; apps/web/src/proxy.ts is reserved for the auth gate.
- Open PR: #2 (dev -> main).
- Blocker: host port 5432 taken by python-playground-db-1; the root
  compose db cannot publish while it runs.
- Running on this host: user's FastAPI on :8000. Do not kill it;
  smoke tests route around it.
