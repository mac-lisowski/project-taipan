# Spec: BFF seam hardening

Status: implemented (PR #20).

Seam: the existing proxy seam in apps/web. This spec hardens its
edges; it adds no new module.

## Problem Statement

The BFF boundary gate enforces names, not the property: it greps
for the literal `API_INTERNAL_URL` and the literal `:8000`, so a
renamed env var or a port-less internal hostname bypasses it. It
also misses untracked files because `git grep` only sees the
index. In the proxy itself, the `try` wraps header and response
construction. A proxy-side bug (a bad `PUBLIC_ORIGIN`, an
unbuildable status) surfaces as `502 upstream unavailable`. No log
line distinguishes it from a real upstream failure. And
`PUBLIC_ORIGIN` is optional in
production even though a missing value silently produces wrong
forwarded-proto headers and mis-rewritten redirects.

## Solution

Extend the gate to the property it means: any upstream-address env
read outside `src/app/api` is a violation, whatever the variable
is called, and untracked files are covered. Narrow the proxy's
`try` to the upstream call so construction bugs are honest errors,
add a log line, and require `PUBLIC_ORIGIN` in production the same
way `API_INTERNAL_URL` is required.

## User Stories

1. As a maintainer, I want the gate to catch upstream-address reads
   under any variable name, so that the boundary holds under
   renames.
2. As a maintainer, I want the gate to see untracked files, so
   that a local run cannot miss a bypass in a new file.
3. As an operator, I want proxy-internal errors distinguishable
   from upstream failures, so that a 502 does not send me chasing
   the wrong side.
4. As an operator, I want `PUBLIC_ORIGIN` required in production,
   so that a missing value fails deploy readiness rather than
   mis-writing redirects.
5. As a developer, I want one log line on upstream failure, so
   that the proxy is not a black box.
6. As a maintainer, I want the env exemption narrowed to actual
   env files, so that a source file containing `.env` in its name
   is not silently exempt.
7. As a developer, I want the `/api/*` forwarding slot documented,
   so that a future path allowlist has an obvious home.
8. As a reviewer, I want the existing gate behavior preserved for
   real violations, so that tightening does not weaken.

## Implementation Decisions

- `check-bff.sh` additionally flags `process.env` reads whose
  names suggest an upstream address (`*_URL`, `*_URI`, `*_ORIGIN`,
  `*_HOST`, `*_ENDPOINT`, `*_INTERNAL`) outside `src/app/api`,
  keeping the same env-file and docs exemptions.
- The check covers untracked files by appending
  `git ls-files --others --exclude-standard` under `apps/web` to
  the scan set.
- The `.*\.env.*` exemption narrows to files matching
  `.env`, `.env.*`, `*.env` basename patterns only.
- `upstream-proxy.ts`: the `try` narrows to the upstream `fetch`
  call; header and response construction errors propagate. The
  catch logs the failure once (`console.error`) and still returns
  502.
- `route.ts`: `PUBLIC_ORIGIN` gains the same production-required
  check as `API_INTERNAL_URL`.
- A code comment marks where a future `/api/*` path allowlist
  plugs in; the policy itself is deferred.
- No new modules; this is edge work on the existing seam.

## Testing Decisions

- Good tests exercise the proxy through `proxyUpstream` as today,
  per `upstream-proxy.test.ts`: a construction-time throw (bad
  `PUBLIC_ORIGIN` value reaching `new URL`) must not surface as a
  502 body.
- Gate tests: run `check-bff.sh` against fixture cases if the repo
  has a harness for script checks; otherwise verify by hand-run on
  a planted violation that is then reverted.
- `route.ts` production check mirrors the existing
  `API_INTERNAL_URL` pattern; cover via the same test conventions
  if route tests exist, else manual verification.
- Prior art: `upstream-proxy.test.ts`,
  `upstream-proxy.response.test.ts`, and the shared
  `testsupport.ts` recording fetch.

## Out of Scope

- A `/api/*` path allowlist policy; the slot is marked for when an
  internal-only upstream route exists.
- Rate limiting, auth gating, or `src/proxy.ts` work.
- Rewrites in `next.config.ts` beyond what the widened env check
  already flags.
- Structured logging or telemetry for the proxy.

## Further Notes

- Candidate 8 from the architecture review, rated speculative
  there: small edge fixes, no new seams. Worth doing cheaply, not
  worth a redesign.
- `docs/specs/implemented/bff-seam-hardening/spec.html` visualizes the gaps.
