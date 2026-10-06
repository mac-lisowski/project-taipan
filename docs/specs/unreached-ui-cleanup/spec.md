# Spec: Unreached UI cleanup

Status: implemented (PR #14).

Seam: none new. This spec deletes modules with zero callers and
keeps the `@/ui` barrel honest about what is library versus dead
page inventory.

## Problem Statement

Roughly 550 lines of apps/web code have no live consumers:
`ReleaseGrid`, `LiveStats`, and `Chrome` are page-level components
no route renders, and they alone consume four `@/ui` exports
(`NewsCard`, `Stat`, `Sparkline`, `CodeTabs`). The landing page that
would have wired them, including the recorded
`dither-background.tsx`, is absent from the working tree on
`feat/web-dither-landing`. The cluster sits under the 300-LOC gate
as speculative surface: adapters with zero callers are not seams,
they are inventory that was never stocked.

## Solution

Delete the three page-level unreached components. Keep the `src/ui`
primitives: the design-system barrel is library surface by rule and
inventory there is normal. Reconcile memory with the tree: the
dither landing work is lost and gets rebuilt deliberately or not at
all. A lightweight unreachable-export check guards against the next
silent accumulation.

## User Stories

1. As a maintainer, I want components with zero importers deleted,
   so that the tree only carries reachable behavior.
2. As a developer, I want the `@/ui` barrel to keep its primitives,
   so that the design system stays stocked for the next page.
3. As a reviewer, I want the deletion to be tree-wide verified, so
   that no import survives by accident.
4. As a maintainer, I want a CI check on unreached `components/`
   exports, so that speculative surface surfaces instead of
   accumulating.
5. As a project owner, I want the lost `dither-background.tsx`
   work acknowledged in the record, so that the discrepancy
   between memory and tree is resolved, not forgotten.
6. As a developer, I want auth forms and docs components untouched,
   so that live paths carry no churn.
7. As a maintainer, I want the decision to wire versus delete made
   explicit, so that the cluster stops sitting in two states at
   once.
8. As a developer, I want `pnpm lint` and `tsc` green after
   deletion, so that removal is provably clean.

## Implementation Decisions

- Delete `release-grid.tsx`, `live-stats.tsx`, and `chrome.tsx`
  from `src/components/`; they are page-level, unreached, and
  verified to have no importers.
- Keep `src/ui` primitives (`NewsCard`, `Stat`, `Sparkline`,
  `CodeTabs`) exported: `src/ui` is the design-system package and
  unused exports there are inventory by convention, not
  pass-throughs.
- Record that `dither-background.tsx` no longer exists in the
  tree; if the landing page returns, its components are rebuilt
  under a separate spec.
- Add a small check (script or lint rule) that flags exported
  `src/components/` modules with zero importers, run in pre-commit
  or CI; it complements the existing BFF and LOC gates.
- No behavior change: nothing deleted is reachable.

## Testing Decisions

- Deletion needs no new tests; the verification is the existing
  gates: `pnpm lint`, `next typegen` + `tsc --noEmit`, and a full
  build to prove no dynamic import hid a consumer.
- The new check is verified by running it against the tree before
  and after deletion: it must flag the cluster before and pass
  after.
- Prior art: `scripts/check-bff.sh` and `scripts/check-file-size.sh`
  for the gate script conventions.

## Out of Scope

- Rebuilding the landing page or the dither background; that is a
  separate spec if wanted.
- Deleting `src/ui` primitives.
- Auth form extraction; covered by its own spec.
- Changing the 300-LOC or BFF gates.

## Further Notes

- Candidate 5 from the architecture review. The deletion test is
  the whole argument: complexity vanishes, nothing reappears.
- `docs/specs/unreached-ui-cleanup/spec.html` visualizes the dead
  surface.
