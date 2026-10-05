# Spec: Auth form module

Status: not implemented.

Seam: `useAuthSubmit` stays the transport seam. This spec adds a
presentational `AuthForm` module on top of it and a `Field`
primitive in `src/ui`.

## Problem Statement

Each of the three auth forms re-implements the same shell: the
`onSubmit` wrapper, the error paragraph markup, the eyebrow label
class string, and the submit-button styling. Roughly 70 percent of
each 76-86 line component is shared boilerplate. The same error
also flows through two channels, `useAuthSubmit`'s `error` state
and the returned `AuthResult.error`, so a form must know both to
render one message.

## Solution

An `AuthForm` module owns the shell: form element, pending state,
error paragraph, submit button, and success callback. Callers
supply only the field set. A `Field` primitive in `src/ui` absorbs
the repeated `Label` + `Input` cluster. The error has one channel:
`useAuthSubmit`'s state, which `AuthForm` renders.

## User Stories

1. As a developer, I want one auth form shell, so that adding a
   fourth form means writing only its fields.
2. As a developer, I want `Field` in the design system, so that
   the label-input cluster is a primitive, not copy-paste.
3. As a maintainer, I want the error rendered in exactly one
   place, so that error markup changes once.
4. As a developer, I want `useAuthSubmit` unchanged as the
   transport seam, so that tested behavior does not move.
5. As a developer, I want the success behavior per form
   (reload, navigate, done state) passed as a callback, so that
   the shell carries no page knowledge.
6. As a reviewer, I want forms to shrink to their field sets, so
   that reading a form shows its fields, not scaffolding.
7. As a maintainer, I want pending-label text per form, so that
   each form keeps its voice.
8. As a developer, I want no new test dependencies, so that the
   extraction lands on existing gates.

## Implementation Decisions

- New `AuthForm` module in `src/components/`: props are
  `endpoint`, `submitLabel`, `pendingLabel`, `onSuccess`, and
  `children` for the fields. It calls `useAuthSubmit` internally,
  renders the shared error paragraph and styled submit button,
  and invokes `onSuccess` when the result is ok.
- New `Field` primitive in `src/ui/components/`: wraps `Label` +
  `Input` + the shared gap and eyebrow classes, accepts
  `className` and merges via `cn()`, exported from the barrel per
  the design-system rule.
- The three forms become the `AuthForm` call plus field markup;
  each keeps its unique navigation behavior (`reload`,
  `router.push`, local done state) via `onSuccess`.
- Error channel: `useAuthSubmit` state is the single display
  source. `submitAuth` keeps returning `AuthResult` because it is
  the pure tested function; `AuthForm` consumes only `result.ok`.
- No new dependencies and no new test infrastructure.

## Testing Decisions

- Good tests stay at the existing seam: `submitAuth` as a pure
  function with a stubbed fetch, per `auth-submit.test.ts`.
- The extraction is structural: `pnpm lint`, `tsc --noEmit`, and a
  build verify the forms compose correctly.
- If hook-level tests are wanted later, that lands with
  `@testing-library/react` as a separate decision; this spec adds
  no infra.
- Prior art: `auth-submit.test.ts` for the stubbed-fetch
  convention.

## Out of Scope

- Real auth endpoints; the forms post to routes that the users
  slice and auth work will eventually serve.
- Form validation beyond what the inputs already carry.
- Session handling, redirects, or `src/proxy.ts` work.
- Changing the proxy or BFF layer.

## Further Notes

- Candidate 7 from the architecture review. Modest leverage win;
  the forms are mock-backed today, so this is preparation for the
  real auth slice.
- `docs/specs/auth-form-module/spec.html` visualizes the collapse.
