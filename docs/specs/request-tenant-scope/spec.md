# Spec: Request-scoped tenant context

Status: not implemented.

Seam: one middleware module owning request-to-tenant scope in the
api app, plus the auth endpoints that mint sessions. Tests cross
the seam through `TestClient` with the lifespan running.

## Problem Statement

`EncryptedString` reads the tenant from `crypto.tenant_scope`.
No production code ever sets that scope. The column cannot be
called from any request path today. There is no login, no
session, and no tenants table. The `User` row has no `tenant_id`.
The web login and register forms post to `/api/auth/login` and
`/api/auth/register`. Those endpoints do not exist. A tenant id
from config would scope every request to one shared value. That
hides which user a row belongs to. The scope must come from the
logged-in user instead.

## Solution

Register creates a personal tenant plus the user. Login checks
the password and mints an opaque session. The session token
travels in an HttpOnly cookie. A middleware resolves cookie to
session to user to `tenant_id` once per request. It wraps the
request in `tenant_scope`. Handlers and the ORM column never
touch the context again. Requests without a valid session run
unscoped. Encrypted writes then fail loudly. A lifespan check
refuses to start the app when encrypted columns exist but no
crypto module is registered. A flush guard asserts rows agree
with the ambient scope.

## User Stories

1. As a visitor, I want register to create my account, so that
   I can log in.
2. As a user, I want login with email and password, so that
   later requests know my tenant.
3. As a user, I want logout, so that my session ends.
4. As a user, I want `GET /api/auth/me`, so that the client
   learns who is logged in.
5. As an api developer, I want the request tenant set in one
   place, so that no handler can forget it.
6. As an api developer, I want `EncryptedString` to work inside
   a request without extra calls, so that adding an encrypted
   column is a one-line model change.
7. As a reviewer, I want sessionless requests to run unscoped,
   so that encrypted writes fail loudly instead of landing
   under a fallback tenant.
8. As a maintainer, I want a flush guard checking row
   `tenant_id` against the ambient scope, so that a mis-scoped
   write raises instead of storing an undecryptable envelope.
9. As an operator, I want the app to refuse startup when
   encrypted columns exist but no crypto module is registered,
   so that missing config is a boot failure, not a 500 at
   first flush.
10. As a test runner, I want the api test client to run the
    lifespan, so that crypto registration is exercised in every
    request test.

## Implementation Decisions

- New `tenants` table: `id` Text primary key, app-generated
  uuid4 hex. The id type matches the crypto tenant id (`str`).
  No database-side generation, so SQLite and Postgres behave
  the same.
- `users` gains `tenant_id` Text, foreign key to `tenants`,
  not null. The Alembic revision backfills one personal tenant
  per existing user. Only dev data exists today.
- New `sessions` table: `token_sha256` Text primary key,
  `user_id` foreign key, `expires_at` timestamptz,
  `created_at`. The cookie holds the raw token
  (`secrets.token_urlsafe(32)`). The database holds only its
  sha256.
- Cookie name `session`. HttpOnly, SameSite=Lax, Path=/. The
  Secure flag stays out until the app serves https only.
- `POST /api/auth/register` takes JSON `{email, password}`.
  It creates a tenant and a user in one transaction. A
  duplicate email returns 409 with `detail`. Success returns
  201 with `UserOut` and sets the session cookie. The existing
  `POST /api/users` creates a personal tenant the same way,
  through one shared helper, so no path can make a
  tenantless user.
- `POST /api/auth/login` takes JSON `{email, password}`.
  Unknown email or bad password returns 401 with a generic
  `detail`. Success sets the session cookie and returns 204.
- `POST /api/auth/logout` deletes the session row and clears
  the cookie. It returns 204 even without a session.
- `GET /api/auth/me` returns 200 `{id, email, tenant_id}`
  with a valid session, else 401. The `tenant_id` comes from
  the ambient scope, so `/me` doubles as the scope probe.
- Session lifetime is 7 days, fixed. No sliding expiry and no
  refresh endpoint.
- `TenantScope` middleware reads the session cookie and loads
  session plus `user.tenant_id` in one short-lived session,
  then closes it. It enters `crypto.tenant_scope` around the
  request. A missing, unknown, or expired session leaves the
  request unscoped. The middleware speaks only `tenant_scope`.
- Lifespan check: after crypto registration, if any mapped
  model uses `EncryptedString` and the module is `None`,
  startup raises instead of serving.
- Flush guard: an ORM `before_flush` hook raises `CryptoError`
  when a dirty object defines `tenant_id` that disagrees with
  the ambient scope. Objects without `tenant_id` are
  unaffected.
- The api `TestClient` fixture runs the lifespan
  (`with TestClient(app)`), so registration and teardown are
  covered by existing request tests.
- No behavior change to existing endpoints, except that user
  creation now also creates a tenant.

## Testing Decisions

- Good tests cross the new seam through HTTP: they assert
  request outcomes and stored rows, never the ContextVar
  directly.
- Register test: 201, sets the cookie, creates one tenant row
  and one user row pointing at it.
- Login test: wrong password returns 401 without a cookie;
  right password sets the cookie; `/me` returns the tenant.
- Logout test: the cookie clears and `/me` returns 401 after.
- Expiry test: a backdated session behaves like no session.
- Scope test: `/me` under one login never reports another
  user's tenant.
- Flush-guard test: a row with `tenant_id="b"` written under
  `tenant_scope("a")` raises and nothing persists.
- Lifespan test: startup fails when columns exist and the
  module is `None` (simulated registration state).
- Prior art: `apps/api/tests/test_encrypted_string.py` for
  column-level scope tests, `conftest.py` session fixtures,
  `TestClient` per the FastAPI skill conventions.

## Out of Scope

- Organizations and shared tenants. One personal tenant per
  user. Tenant rows never merge.
- Password reset. `/api/auth/forgot` stays unimplemented; the
  web form keeps failing until a reset spec lands.
- Session listing, revocation endpoints, remember-me, sliding
  expiry.
- Login rate limiting.
- Per-tenant KMS keys.
- Background-job scope helpers beyond the documented rule.
- Changes to the crypto package.

## Further Notes

- This replaces the earlier resolver-port draft with an env
  default tenant. That draft is deleted: tenant scope comes
  from the logged-in user, never from config.
- Implements ADR-0001's `tenants` table and the "one request
  = one tenant" assumption.
- The users-slice refactor later moves the register paths
  into the users module. This spec does not block on it.
- `docs/specs/request-tenant-scope/spec.html` visualizes the
  seam.
