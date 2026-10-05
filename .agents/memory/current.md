# Current state

- Last updated: 2026-10-05
- On dev: bff-proxy-module spec implemented (PR #7, 8381fca).
  infisical-kms implemented (PR #5). All five specs in docs/specs/
  now carry a Status line. Not implemented: kms-identity-adapters,
  encryption-seam (ADR only), users-slice.
- Workflow: implement-spec runs ticket by ticket; review-stamp before
  every commit; PR to dev when the user asks.
- Next step: pick and spec the next slice. Candidates by review
  priority: users-slice, then kms-identity-adapters, encryption-seam.
  Auth/session layer: FastAPI owns sessions in Redis via
  API_REDIS_URL; apps/web/src/proxy.ts is reserved for the auth gate.
- Open PR: #2 (dev -> main).
- Blocker: host port 5432 taken by python-playground-db-1; the root
  compose db cannot publish while it runs.
- Running on this host: user's FastAPI on :8000. Do not kill it;
  smoke tests route around it.
