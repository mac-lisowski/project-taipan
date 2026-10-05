# Spec: Deepen the users slice

Status: not implemented.

Seam: a `users` module with a small interface over an injected
SQLAlchemy `Session`. One seam. Routers and tests cross the same
interface.

## Problem Statement

User registration semantics live in the HTTP router: the email
uniqueness check, password hashing, and model construction are all
in the POST handler. The 404-on-missing dance is duplicated across
handlers. The repository layer is a shallow pass-through to the
SQLAlchemy session: its interface is nearly its implementation, so
it concentrates nothing. The result is that domain rules can only
be exercised through HTTP plus a database, and a rule change means
editing the adapter.

## Solution

A `users` module owns the rules: `register`, `get`, `list`,
`remove`, over an injected `Session`. Uniqueness violations raise a
typed domain error, not an `HTTPException`. The router becomes a
thin adapter mapping the domain error to 409 and missing users to
404. Tests exercise the module directly against the real test
database session, without TestClient or HTTP semantics.

## User Stories

1. As a developer, I want registration rules in a `users` module,
   so that creating a user does not require an HTTP request.
2. As a developer, I want `register(email, password)` returning a
   `User`, so that call sites pass domain types, not HTTP schemas.
3. As a developer, I want duplicate email to raise a typed
   `EmailTaken` error, so that callers map it to their own error
   mode (HTTP 409, CLI message, test assertion).
4. As a developer, I want get-or-missing handled once inside the
   module, so that handlers stop duplicating the 404 branch.
5. As a test runner, I want tests driving the module with a real
   session, so that rules are verified without the HTTP stack.
6. As a developer, I want the router reduced to status-code
   mapping, so that reviewing domain rules means reading one file.
7. As a developer, I want password hashing invoked inside the
   module, so that no call site can store an unhashed password.
8. As a maintainer, I want the module interface to stay small
   (register, get, list, remove), so that the contract is obvious.
9. As a developer, I want the module free of FastAPI imports, so
   that it is usable from scripts and tests without the framework.
10. As a developer, I want existing endpoint behavior unchanged,
    so that the refactor cannot break the API contract.
11. As a maintainer, I want the repository layer deleted once the
    module uses the session directly, so that no second
    persistence path survives to drift.

## Implementation Decisions

- New `users` module inside the api app. It exposes functions
  taking a `Session` plus domain arguments. It returns `User`
  objects and raises typed errors.
- The module uses the injected `Session` directly, not the
  repository. `BaseRepository` and `UserRepository` are deleted in
  this spec: field-encryption deferred the deletion here, and
  ADR-0001 rules them deletable. Once the module exists, nothing
  calls them.
- The module raises a domain error on duplicate email. The router
  catches it and returns 409. Missing-user lookups return a typed
  `NotFound` the router maps to 404.
- Routers lose all rule logic. They keep: dependency injection,
  schema validation via request/response models, and error-to-
  status mapping.
- `security.py` is unchanged. The users module calls it; hashing
  policy stays in one place either way.
- The commit boundary moves out of `BaseRepository.add/delete`.
  Today `add()` commits the entire session, including unrelated
  pending state. The `get_db` teardown owns commit instead: the
  session commits when the request completes cleanly and rolls
  back on error. The repository and the users module flush at
  most; neither commits.
- No schema changes. No new endpoints. No behavior change visible
  through the HTTP contract.

## Testing Decisions

- Good tests call the module with a real test-database session
  and assert on returned objects and raised errors. They do not
  touch HTTP.
- New module tests: register creates a user with a hashed (not
  raw) password; duplicate email raises `EmailTaken`; get returns
  the user; get on missing id raises the not-found error; remove
  deletes; list returns users.
- Existing HTTP tests stay and keep passing unchanged; they now
  also pin the error-to-status mapping.
- A test pins the new commit boundary: a handler error after a
  write attempt leaves no partial row, and a clean POST persists
  without any module-level commit.
- Prior art: `apps/api/tests/test_users.py` for the HTTP layer;
  the same `API_TEST_*` session conventions for module tests,
  skip-when-DB-down per apps/api rules.
- After editing tests: `uvx falsegreen`, then `test-smell-review`.

## Out of Scope

- Auth endpoints, login, sessions, tokens.
- Encrypted columns or KMS integration.
- Schema or migration changes.

## Further Notes

- Candidate 2 from the architecture review. The payoff is mostly
  locality ahead of growth: auth and sessions land in this slice
  next, and they should land on a deep module, not in routers.
  The review added the commit-boundary relocation: the repository
  slated for deletion secretly owns the app's only commit, so it
  moves to session teardown before the repo goes.
- `docs/specs/users-slice/spec.html` visualizes the refactor.
