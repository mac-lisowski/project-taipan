# Spec: First-run setup wizard

Status: planned.

Seam: the HTTP boundary. Api tests cross `POST/GET /api/setup` and the
user routes through the test client. Web tests cross the form and gate
components with vitest. No new internal seams.

## Problem Statement

A fresh deployment has no users. There is no way in without manual
database work, because registration is the only account-creation path
and it carries no privilege. Meanwhile self-registration is open to
anyone forever, so a "first user" means nothing today. The operator
needs a first-run flow: create the platform admin, log in, close
open registration.

## Solution

When the `users` table is empty, the login page shows a setup form
instead of the login form. Submitting creates the first user, grants
the `admin` role, sets the session cookie, and lands on a minimal
`/account` page. Afterwards the probe reports setup complete, the
setup endpoint refuses, and open self-registration is closed. The
admin manages further users through the gated user routes.

## User Stories

1. As an operator on a fresh deploy, I want the app to detect that no
   users exist, so that I am offered first-run setup instead of a
   login that cannot succeed.
2. As an operator, I want to create the first account with email and
   password, so that I get in without touching the database.
3. As the first user, I want to be logged in right after setup, so
   that I do not repeat my credentials on a login form.
4. As the first user, I want the `admin` role, so that privileged
   routes have an owner from the first minute.
5. As an operator, I want self-registration to close after setup, so
   that strangers cannot mint accounts on my instance.
6. As an operator, I want a second setup submission to fail, so that
   two concurrent first-run requests cannot both create an admin.
7. As an admin, I want to create regular users through a gated route,
   so that my team can get accounts without open registration.
8. As an admin, I want the user list and delete routes gated, so that
   user management is not world-writable.
9. As a signed-in user, I want `/` to send me to `/account`, so that
   I do not see a login form I no longer need.
10. As a signed-in user, I want `/account` to show my id, email,
    tenant, and roles, so that I can confirm my session works.
11. As a visitor without a session, I want `/account` to send me back
    to `/`, so that protected pages are not reachable signed out.
12. As an operator rerunning setup on an initialized instance, I want
    a clear refusal, so that I know the instance is already set up.
13. As a deployer upgrading a database that already has users, I want
    the earliest user to become admin, so that the instance does not
    end up with no admin at all.

## Implementation Decisions

- New probe endpoint `GET /api/setup` returns `{"needs_setup": bool}`.
  It is unauthenticated and answers `SELECT count(*) FROM users == 0`.
  It is the only signal the web side needs; an unauthenticated probe
  that reveals "instance not set up" is the standard install-wizard
  tradeoff.
- New endpoint `POST /api/setup` replaces `POST /api/auth/register` as
  the public account-creation path. Body `{email, password}`. While
  `users` is empty it creates tenant + user + `user_tenants` link +
  `admin` role + session cookie and returns 201 `UserOut`. When any
  user exists it returns 409 `{"detail": "setup already completed"}`.
- Single-shot enforcement is DB-level, not a count check: the
  bootstrap function takes a transaction-scoped
  `pg_advisory_xact_lock` on a fixed key, then rechecks the count
  inside the lock. The second concurrent requester blocks, then sees
  a non-empty table and gets 409. Per the users-slice convention the
  lock, recheck, and orchestration live in the users/auth module; the
  router only maps the outcome to 201 or 409.
- `POST /api/setup` is indifferent to an inbound session cookie: when
  users exist it returns 409 anyway; on an empty table no valid
  session can exist because `sessions.user_id` cascades on user
  delete.
- `POST /api/auth/register` is removed. Open self-registration is gone
  for good; the only public creation path is the single-shot setup
  endpoint. The web `/register` page is removed with it.
- Roles are a Pattern A extension table `user_roles`: `user_id` FK to
  `users` with cascade delete, `role` text with
  `CHECK (role = 'admin')`, `unique(user_id, role)`. `users` gains no
  columns. Widening the CHECK for a future role needs a migration.
  `user_roles` carries no `tenant_id`, so the tenant flush guard does
  not apply to it.
- The Alembic migration creates `user_roles` and backfills `admin` to
  the earliest user (`ORDER BY created_at, id LIMIT 1`) when users
  exist and no roles do. This keeps an upgraded instance admin-able.
  Known limit: an instance that later loses all role rows has no
  self-service recovery; `POST /api/setup` keeps returning 409 and a
  manual insert is the fix.
- New dependency `require_admin` resolves the session cookie to a
  user, then requires the `admin` role. No session → 401, session
  without role → 403. It is the first real authorization check.
- `require_admin` gates the users router object (list, create, get,
  delete) - not every path under `/users`. The profiles router shares
  the `/users` prefix but is a separate `APIRouter` and stays open.
  Per-user (self-service) authorization is a later spec.
- `POST /api/users` keeps its current body and still calls the
  register helper (tenant + link), but sets no cookie and grants no
  role. With register gone, it is the only way a second user is born.
- `GET /api/auth/me` gains a `roles` field so the web app can render
  admin state without a second call.
- Web `/` stays a server component. It reads the `session` cookie via
  `cookies()`: present → `redirect("/account")` (presence only;
  `/account` validates). Absent → render a client gate component that
  fetches `/api/setup` through the BFF catch-all, shows a loading
  shell, then renders the setup form or the login form. The cookie
  check cannot live in the client gate: the cookie is HttpOnly.
  Reading `cookies()` makes `/` dynamic, which is acceptable.
- The `/register` page and route are removed. The `/register` link in
  the login form is dropped in the same change.
- `register-form.tsx` is repurposed as `setup-form.tsx` posting to
  `/api/setup` (the unreached-components gate would flag an orphaned
  component otherwise). The stale "route does not exist yet" comment
  and the extra `name` field are dropped. On success it navigates
  straight to `/account` (`router.push`), since the cookie is already
  set.
- New `/account` page in its own route group (not under `(public)`,
  which owns the auth-panel shell). Server component: no `session`
  cookie → `redirect("/")`; otherwise it calls FastAPI directly via a
  new fetch helper module inside `src/app/api/` - the only directory
  the BFF gate allows upstream env reads in - passing the inbound
  session cookie as the `Cookie` header and `cache: "no-store"`. On
  401 it redirects to `/`. A server component cannot use a relative
  `fetch`, and deriving an origin from the request `Host` header was
  rejected: it adds a loopback hop and trusts client-controlled input.
- LoginForm success keeps `window.location.reload()`; the server-side
  cookie check on `/` then redirects to `/account`. No new wiring.

## Testing Decisions

- Api tests cross HTTP only, through the existing test client and
  real `app_test` database. Prior art: `tests/test_auth.py`,
  `tests/test_users.py`.
- `GET /api/setup`: 200 `{"needs_setup": true}` on empty table, false
  after any user exists.
- `POST /api/setup`: 201 + cookie + `user_tenants` link + admin role
  on first call; 409 on second call; 409 after a plain user exists;
  409 even when a session cookie is supplied.
- Concurrency: two sequential calls pin the lock path; a threaded
  double-submit may be added but sequential 409 is the required test.
- `register` is gone: a request to `/api/auth/register` returns 404,
  not a 500.
- `require_admin`: 401 without session, 403 for a session whose user
  lacks the role, 200-class for admin. Pin one test per route method.
- `/api/auth/me` returns `roles: ["admin"]` for the bootstrap user.
- Migration test on the existing scratch-DB harness
  (`test_migrations.py`): upgrade to the pre-roles revision, seed two
  users, upgrade to head, assert the earliest user gained `admin` and
  the other did not. Prior art: the tenancy backfill test.
- Removing `POST /api/auth/register` breaks every test that used it
  to mint a session (`test_auth.py`, `test_tenant_scope.py`,
  `test_users.py`). They rebase onto a shared fixture that runs
  `POST /api/setup` once per test; a second user where needed comes
  from an admin-session `POST /api/users`.
- Web vitest follows the no-React-render convention (`auth-submit`,
  docs-url-policy specs): extract the gate's probe-to-form decision
  and the `/account` redirect predicate into pure functions and test
  those with `vi.stubGlobal("fetch")`; components stay thin adapters
  verified by lint, typecheck, and build.

## Out of Scope

- Per-user authorization and ownership checks on profiles.
- Invites, password reset (`/api/auth/forgot`), email verification.
- Admin UI for user management beyond the gated routes.
- Rate limiting or captcha on the setup endpoint.
- Org tenants, additional roles beyond `admin`.
- Session rotation, `Secure` cookie flag (needs TLS).

## Further Notes

- Pattern A extension-table decision:
  `.agents/memory/decisions/extensible-entities-pattern-a.md`;
  tenant link precedent:
  `.agents/memory/decisions/tenant-link-extension-table.md`.
- `docs/specs/planned/setup-wizard/spec.html` visualizes the seam
  and the closed-registration switch.
