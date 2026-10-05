# Spec: Request-scoped tenant context

Status: not implemented.

Seam: one middleware module owning request-to-tenant-scope in the
api app, plus a startup wiring check. Tests cross the seam through
`TestClient` with the lifespan running.

## Problem Statement

`EncryptedString` reads the tenant from `crypto.tenant_scope`, but
no production code ever sets that scope: the column cannot be
called from any request path today. When the first real encrypted
column lands, every handler must remember to establish scope. A
handler that forgets fails at flush time. In background jobs it
silently encrypts under a stale scope. Separately,
the api test fixture never runs the lifespan, so the crypto
module's registration is unexercised, and nothing stops a scope
that disagrees with a row's own `tenant_id` from producing an
envelope that is permanently undecryptable.

## Solution

A `TenantScope` middleware resolves the tenant once per request
through an injectable resolver port and wraps the request in
`tenant_scope`. Handlers and the ORM column never touch the context
again. A lifespan check refuses to start the app when encrypted
columns exist but no crypto module is registered, so missing config
fails at boot rather than at first flush. A flush-time guard
asserts that rows carrying a `tenant_id` agree with the ambient
scope, converting silent cross-tenant encryption into an error.

## User Stories

1. As an api developer, I want the request's tenant scope set in
   one place, so that no handler can forget it.
2. As an api developer, I want `EncryptedString` to work inside a
   request without extra calls, so that adding an encrypted column
   is a one-line model change.
3. As a maintainer, I want tenant resolution behind a resolver
   port, so that the rule changes from "default tenant" to
   "authenticated user" without touching the middleware or column.
4. As an operator, I want the app to refuse startup when encrypted
   columns exist but no crypto module is registered, so that
   missing Infisical config is a boot failure, not a 500 at first
   flush.
5. As a reviewer, I want requests that cannot resolve a tenant to
   run unscoped, so that encrypted writes fail loudly instead of
   landing under a fallback tenant.
6. As a maintainer, I want a flush guard checking row `tenant_id`
   against the ambient scope, so that a mis-scoped write raises
   instead of storing an undecryptable envelope.
7. As a developer, I want background jobs to keep setting scope
   per unit of work explicitly, so that the documented rule stays
   enforceable.
8. As a test runner, I want the api test client to run the
   lifespan, so that crypto registration is exercised in every
   request test.
9. As a test writer, I want to stub the tenant resolver in tests,
   so that scope behavior is verifiable without auth.
10. As a developer, I want the middleware free of crypto package
    internals, so that it speaks only `tenant_scope` and the
    resolver port.

## Implementation Decisions

- New tenant-scope module in the api app: an HTTP middleware plus a
  `tenant_for(request) -> str | None` resolver port.
- The middleware enters `crypto.tenant_scope` around the request
  when the resolver returns a tenant; on `None` it leaves the
  context unset so encrypted columns fail with
  `MISSING_TENANT_SCOPE` on use.
- First resolver adapter: an env-configured default tenant
  (`API_TENANT_ID`), matching today's single shared DEK posture.
  When auth lands, a session-backed adapter replaces it at the
  composition root; middleware and column stay unchanged.
- The composition root wires the resolver; the middleware is
  registered in the app factory next to the lifespan.
- Lifespan check: after crypto registration, if any mapped model
  uses `EncryptedString` and the module is `None`, startup raises
  instead of serving.
- Flush guard: an ORM `before_flush` hook raises `CryptoError`
  when a dirty object defines `tenant_id` that disagrees with the
  ambient scope. Objects without `tenant_id` are unaffected. This
  enforces the ADR-0001 "one tenant scope per flush" rule at
  runtime for the case that can corrupt data.
- The api `TestClient` fixture runs the lifespan
  (`with TestClient(app)`), so registration and teardown are
  covered by existing request tests.
- No schema changes. No behavior change to existing endpoints:
  they carry no encrypted columns today.

## Testing Decisions

- Good tests cross the new seam through HTTP: they assert request
  outcomes and stored ciphertext, never the ContextVar directly.
- Middleware tests: a stubbed resolver + TestClient proves the
  scope reaches the column (a test-only endpoint or model write
  asserts the envelope, or `current_tenant` inside a probe
  endpoint); a `None` resolver leaves requests unscoped.
- Lifespan test: the fixture change itself exercises
  `build_and_register_field_crypto` on every api test; an explicit
  test asserts startup fails when columns exist and the module is
  `None` (simulated registration state).
- Flush-guard test: a row with `tenant_id="b"` written under
  `tenant_scope("a")` raises and nothing persists.
- Prior art: `apps/api/tests/test_encrypted_string.py` for
  column-level scope tests, `conftest.py` session fixtures,
  `TestClient` per the FastAPI skill conventions.

## Out of Scope

- Authentication, sessions, or deriving the tenant from a logged-in
  user; the resolver port is the seam for that.
- Per-tenant KMS keys (the resolver returns tenant ids, not key
  ids; key topology is unchanged).
- Moving tenant scope establishment into the crypto package; the
  package stays framework-free.
- Background-job scope helpers beyond the documented rule.

## Further Notes

- Candidate 1 (top recommendation) from the architecture review.
  Implements ADR-0001's "one request = one tenant" assumption, which
  nothing had built yet.
- `docs/specs/request-tenant-scope/spec.html` visualizes the seam.
