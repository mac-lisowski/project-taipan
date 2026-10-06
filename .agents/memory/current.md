# Current state

- Last updated: 2026-10-06. dev == origin/dev at c77fbdd, plus an
  uncommitted docs-overhaul working tree (not committed on request).
- Docs overhaul pass (uncommitted): README rewritten to public-facing
  product docs (features, API surface table, roadmap; sessions =
  Postgres not Redis). Fixed stale claims: API_REDIS_URL is DEK L2
  cache not session store (.env.example, devcontainer docs, compose
  comment), devcontainer docs now cover infisical/infisical-db +
  API_INFISICAL_URL, .env.example gained API_KMS_BREAKER_THRESHOLD/
  COOLDOWN, web .env.example gained DOCS_DIR. Spec self-links moved to
  docs/specs/implemented/*. docs/learnings/ deleted on user request;
  docs.ts nav order and docs-url.test.ts slugs updated (learnings ->
  guides). evals/README.md added. Reviewer-verified twice; remaining
  known gap: infisical-kms spec dir lacks spec.html (historical).
- Tenant scope shape: POST /api/auth/register creates tenant + user +
  user_tenants link inside crypto.tenant_scope, one commit via get_db;
  sets cookie `session` (raw token, sha256 in DB, 7 day expiry,
  HttpOnly/Lax/Path=/, no Secure). login 204+cookie/generic 401,
  logout always 204, GET /api/auth/me returns {id,email,tenant_id}
  from ambient scope or 401 (session without link included).
- TenantScopeMiddleware (apps/api/src/api/middleware.py) resolves
  cookie -> sessions.tenant_id_for_token (one join, expiry inline) in a
  short-lived SessionLocal, wraps request in tenant_scope; unresolved
  sessions run unscoped. MUST use db_module.SessionLocal so conftest
  monkeypatch reaches it.
- before_flush guard (api/tenant_guard.py, installed at db.py import)
  raises CryptoError(MISSING_TENANT_SCOPE) when a new/dirty object's
  __dict__ tenant_id disagrees with ambient (absent ambient counts).
  PostgresDekStore.put self-scopes its write to the row tenant.
- Lifespan check: main.py raises RuntimeError when any Base.metadata
  column is EncryptedString and get_field_crypto() is None. conftest
  client fixture runs real lifespan (`with TestClient(app)`) with
  build_and_register_field_crypto monkeypatched to a StubCipher/
  MapStore FieldCrypto.
- No model uses EncryptedString yet; crypto capability is wired but
  dormant. No authorization on /api/users* or profile routes.
- BFF hardening: upstream-proxy try wraps only the fetch; fetch errors
  log once and 502; construction/response errors propagate. Route
  requires PUBLIC_ORIGIN in production. check-bff.sh covers
  tracked+untracked files, env exemption narrowed to real basenames.
- Pattern A ruling: user-to-tenant link is user_tenants extension row
  (user_id unique FK cascade, tenant_id NOT NULL FK). Decision file:
  decisions/tenant-link-extension-table.md.
- Test state: api 77 passed / 2 skips (Postgres, both :15432 and
  :5432 app_test DBs). Web vitest 68/68.
- Trap: a test DB holding tables unknown to the current branch's
  Base.metadata breaks conftest drop_all (dependent FKs). Fix is
  DROP SCHEMA public CASCADE + recreate; conftest rebuilds.
- Devcontainer/host share bind-mounted .git/hooks: last
  `pre-commit install` wins; reinstall on the side you commit from.
- Ops notes: devcontainer DB password reset to postgres:postgres on
  port 15432. Infisical live-run token + mint sequence at
  /tmp/taipan-infisical-kms-notes/token.md (ephemeral).
Activity mode: docs. Set when the phase changes: bash
.agents/hooks/agent-mode.sh set <plan|implement|test|review|debug|docs|commit>
(AGENTS.md rule 10).
