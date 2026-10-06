# Spec: Docs URL policy module

Status: implemented (PR #16).

Seam: `lib/docs.ts` in apps/web owns all docs URL policy.
`Markdown` delegates to it; tests cross it as pure functions.

## Problem Statement

Relative links and asset paths in docs markdown are rewritten
against `/docs/` as if every doc lived at the root, because
`Markdown`'s interface is `{ source }` and lacks the document's
location. The result is a verified live 404: `docs/learnings/
README.md` links to `agents/README.md` and renders
`/docs/agents/README` instead of `/docs/learnings/agents/README`.
`../` links are unhandled. Separately, the path-containment rule
that keeps `docs/` reads inside the directory is implemented twice,
once in `readDoc` and once in the docs-asset route, so a policy
change must be made twice.

## Solution

Three pure functions in `lib/docs.ts` own URL policy:
`docHref(slug, href)` resolves a markdown link against the source
doc's slug into a `/docs/` path; `assetHref(slug, src)` does the
same for images into `/docs-asset/`; `resolveDocPath(parts)` is
the single containment check both `readDoc` and the docs-asset
route call. `Markdown` receives `slug` and delegates; the page
already knows the slug.

## User Stories

1. As a docs reader, I want relative links to resolve correctly,
   so that cross-references inside sections do not 404.
2. As a docs author, I want `../` links to resolve, so that specs
   can link upward to guides and ADRs.
3. As a docs author, I want image sources resolved relative to the
   doc's directory, so that assets sit beside the markdown.
4. As a maintainer, I want one containment function, so that
   tightening the rule (symlinks, hidden files) happens once.
5. As a developer, I want `Markdown`'s interface to carry the
   slug, so that the component has enough information to be
   correct.
6. As a test writer, I want URL policy as pure functions, so that
   every edge case is unit-tested without rendering React.
7. As a developer, I want anchor links, external URLs, and
   absolute paths passed through untouched, so that only relative
   references are rewritten.
8. As a maintainer, I want `rewriteHref`/`rewriteAsset` logic out
   of the JSX file, so that rendering and URL policy live in
   different modules.
9. As a reviewer, I want the docs-asset route and `readDoc` to
   share `resolveDocPath`, so that the two cannot drift.
10. As a developer, I want heading ids to keep working, so that
    the TOC and deep links are unaffected.

## Implementation Decisions

- `lib/docs.ts` gains `docHref(slug, href)`, `assetHref(slug,
  src)`, and `resolveDocPath(parts): string | null`.
- `docHref`: `#` and absolute URLs and `/` paths pass through;
  relative references resolve against `slug` minus its last
  segment (the doc's directory), `.md` is stripped, the result is
  prefixed `/docs/`.
- `assetHref`: same resolution, `/docs-asset/` prefix; external
  and absolute sources pass through.
- `resolveDocPath` resolves `DOCS_DIR + parts`, returns `null`
  when the result escapes the root; both `readDoc` and the
  docs-asset route call it. The route keeps its extension
  allowlist on top.
- `Markdown`'s props become `{ source, slug }`. The rewrite helpers
  move out of the component file; the component keeps rendering
  policy only.
- The docs page passes the slug it already has.
- Traversal that escapes the docs root yields no link change for
  `docHref` (leave the href, it will 404 harmlessly) and `null`
  from `resolveDocPath` for file reads.
- No new dependencies.

## Testing Decisions

- Good tests are pure unit tests on `docHref`, `assetHref`, and
  `resolveDocPath`: `./x.md`, `x.md`, `../x.md`, nested `a/b.md`,
  `#anchor`, `https://`, absolute `/x`, root-escaping traversal.
- No React rendering in tests; the component stays a thin adapter
  verified by typecheck and the docs pages building.
- Prior art: `upstream-proxy.test.ts` and `auth-submit.test.ts`
  for vitest conventions in this app.
- The verified 404 becomes a regression test in
  `apps/web/src/lib/docs-url.test.ts`: a relative link from a section
  README resolves inside that section, not at the docs root.

## Out of Scope

- Rendering changes (typography, code blocks, mermaid).
- `extractHeadings` fence-awareness and heading-id dedup.
- `listDocs` caching.
- New docs features (search, versioning).

## Further Notes

- Candidate 4 from the architecture review. The fix is an
  interface fix: `Markdown` was under-provisioned, not buggy in
  isolation.
- `docs/specs/implemented/docs-url-policy/spec.html` visualizes the seam move.
