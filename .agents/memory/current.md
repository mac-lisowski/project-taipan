# Current state

- Last updated: 2026-10-05
- kms-identity-adapters spec implemented: PR #8 opened to dev from
  feat/kms-identity-adapters (commits 9b86988 transport + cipher,
  6c7740f provisioner replaces InfisicalKms, spec status marked).
  Both tickets done with reports in .scratch/kms-identity-adapters/issues/.
  Package exports: InfisicalCipher, InfisicalProvisioner, KmsError,
  Cipher, Provisioning.
- KmsError gotcha: httpx2 retries a request whose response was lost
  on a dropped keep-alive; idempotent DELETEs can 404 on the retry.
  Test teardown tolerates that case. learnings/httpx2-retry-lost-response.md
- Workflow: implement-spec runs ticket by ticket; review-stamp before
  every commit; PR to dev when the user asks; user reviews diffs
  before commits when asked.
- Next step: after PR #8 merges, next spec per priority: users-slice,
  encryption-seam (ADR first). Auth/session layer after users:
  FastAPI owns sessions in Redis via API_REDIS_URL;
  apps/web/src/proxy.ts reserved.
- Open PR: #2 (dev -> main).
- Blocker: host port 5432 taken by python-playground-db-1; the root
  compose db cannot publish while it runs.
- Running on this host: user's FastAPI on :8000. Do not kill it;
  smoke tests route around it.
