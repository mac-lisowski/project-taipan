# Current state

- Last updated: 2026-10-05
- encryption-seam spec implemented: ADR-0001 accepted at
  docs/adr/ADR-0001-seam-for-encrypted-model-fields.md, backed by a
  throwaway prototype (.scratch/encryption-seam/, delete after PR
  merges). Decisions: EncryptedString TypeDecorator + deep crypto
  module; envelope encryption (per-tenant DEK, AES-256-GCM, wrapped
  by Infisical KMS key, DEK cached in Redis); key id inside the
  envelope (v1:key_id:nonce:ct); generic tenant_id tenancy (tenants
  table; tenant may be user or org; orgs optional; crypto module
  never sees tenant type). Repositories get deleted in the feature
  spec. Verified constraint: one tenant scope per flush.
- Uncommitted on dev: ADR + spec status + decisions index + memory.
  Prototype is scratch (gitignored).
- Workflow: implement-spec runs ticket by ticket; review-stamp before
  every commit; PR to dev when the user asks; user reviews diffs
  before commits when asked.
- Next step: user reviews ADR; commit + PR to dev. Then the field-
  encryption feature spec (first encrypted field, deletes repos,
  adds cryptography dep, blind indexes per field). users-slice still
  not implemented; auth/session layer after users (FastAPI owns
  sessions in Redis via API_REDIS_URL; apps/web/src/proxy.ts reserved).
- Open PR: #2 (dev -> main).
- Blocker: host port 5432 taken by python-playground-db-1; the root
  compose db cannot publish while it runs.
- Running on this host: user's FastAPI on :8000. Do not kill it;
  smoke tests route around it.
