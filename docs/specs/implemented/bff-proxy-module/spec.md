# Spec: Deepen the BFF upstream-proxy module

Status: implemented (#7)

Seam: the new proxy module's interface over standard Fetch
`Request`/`Response` types. One seam. The route handler stays
untested framework glue.

## Problem Statement

The catch-all BFF route handler is the largest source file in the
repo. It fuses real security policy (untrusted-header stripping,
cookie host-binding, redirect rewriting, path re-encoding,
hop-by-hop hygiene) with Next.js plumbing. The only way to exercise
the policy today is to run a Next server and send real requests.
`apps/web` has no tests, so the riskiest code in the repo is also
the least verified. A regression in header hygiene would ship
silently.

## Solution

Extract the proxy policy into a deep module with a small interface:
a standard `Request` plus an upstream base URL go in, a `Response`
comes out. The route handler becomes a thin adapter that translates
`NextRequest` into `Request` and the module's `Response` into
`NextResponse`. All policy moves behind the module's seam, where
unit tests can drive it with plain `new Request()` objects. No
behavior change for callers or browsers.

## User Stories

1. As a developer, I want the proxy policy testable without
   Next.js, so that security rules are verified by unit tests.
2. As a developer, I want all header-hygiene rules in one module,
   so that a rule change is a single edit.
3. As a reviewer, I want the route handler reduced to type
   translation, so that proxy policy audits have one file to read.
4. As a test runner, I want tests that construct standard
   `Request` objects, so that no dev server or network is needed.
5. As a developer, I want a test proving client-supplied
   `x-forwarded-*` headers never reach upstream, so that the
   spoofing protection cannot regress.
6. As a developer, I want a test proving upstream cookie `Domain`
   attributes are stripped, so that cookies stay host-bound.
7. As a developer, I want a test proving upstream `Location`
   headers are rewritten to the public origin, so that redirects
   never leak the internal host.
8. As a developer, I want a test proving path segments are
   re-encoded, so that `%2F`-style inputs cannot reshape the
   upstream path.
9. As an operator, I want `API_INTERNAL_URL` and `PUBLIC_ORIGIN`
   resolution unchanged, so that existing deploys keep working.
10. As a CI job, I want a JS test runner wired for `apps/web`, so
    that the new tests run on every push.
11. As a maintainer, I want the module to stay under the 300 LOC
    cap, so that it fits the repo's gates.
12. As a developer, I want upstream failure mapped to a 502 and a
    bad path to a 400, tested, so that error behavior is pinned.

## Implementation Decisions

- New module in `apps/web`, placed outside `src/app/api/` but still
  inside the BFF boundary. It exports one function taking a
  standard `Request`, an upstream base URL, and a config object;
  it returns a standard `Response`.
- Env vars are read only in the route handler and passed in as
  config. `check-bff.sh` forbids `API_INTERNAL_URL` outside
  `src/app/api/`; the deep module must not read `process.env`.
  This also keeps tests free of env manipulation.
- All five policies move intact: hop-by-hop and untrusted-header
  stripping, forwarding headers rebuilt from trusted values,
  response-header rewriting, cookie host-binding, `Location`
  rewriting, path segment re-encoding, no-body status handling,
  upstream timeout and abort composition.
- The route handler keeps only: params validation, `NextRequest`
  to `Request` adaptation, the module call, and `Response` to
  `NextResponse` adaptation. Target under ~40 lines.
- `fetch` is injected or wrapped so tests can stub the upstream
  without a network. Simplest shape: the module accepts an
  optional fetch implementation defaulting to global `fetch`.
- Add a JS test runner for `apps/web` (vitest) as a devDependency.
  This is the first test setup on the web side.
- Pure refactor: proxying semantics are byte-for-byte identical.
  No new features, no dropped protections.
- `src/proxy.ts` stays reserved for the future auth gate. It is a
  different module at a different seam; do not reuse the name.

## Testing Decisions

- Good tests assert external behavior through the module seam: a
  `Request` in, inspect the `Response` and the arguments the stub
  fetch received. No tests on internal helpers.
- The seam is pure and synchronous enough for plain unit tests.
  No Next server, no real network, no env vars.
- Cases: untrusted headers stripped upstream; forwarding headers
  set from trusted values; hop-by-hop and `connection`-listed
  headers dropped; `set-cookie` re-emitted host-bound; `location`
  rewritten to the public origin; encoded path segments cannot
  reshape upstream; no-body statuses drop the body; upstream
  throw maps to 502; bad segments map to 400.
- Prior art: none on the web side. The repo convention of testing
  through real seams applies: here the seam is a function, so no
  infra is needed.
- After editing tests: `uvx falsegreen` equivalent for TS
  (`npx --yes falsegreen-js`), then `test-smell-review`.

## Out of Scope

- The Next 16 auth gate (`src/proxy.ts` remains reserved).
- Any change to proxy semantics: timeouts, header sets, cookie
  policy, redirect rules all keep their current behavior.
- FastAPI-side header trust rules.
- Streaming or WebSocket upgrades beyond current pass-through.

## Further Notes

- Candidate 1 (Strong) from the architecture review. Origin:
  `docs/specs/bff-proxy-module/spec.html` visualizes the
  before/after module shape.
- The module earns its depth immediately: it is the only
  security-critical code in `apps/web`, and the seam makes it
  testable for the first time.
