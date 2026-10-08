# Spec: BFF result module

Status: implemented (PR #43).

Seam: one web lib module owns the API call result. Call forms, the
settings page, and the register forms consume it. Lib never imports
from app.

## Problem Statement

The ok and error result shape is declared in four web files. The
verbatim detail parsing is written twice. Register lib imports the
switch read result type from the app api directory, so lib depends on
app, an inverted layer. Every new form re-declares the same shape and
risks a different error surface.

## Solution

One lib module owns the client side result: the type, the same origin
JSON calls, and the detail parsing that surfaces the API's error string
verbatim. Auth submit, register, the password change result, and the settings
switch consume it.
The server side upstream resolver keeps its own seam, since server
components cannot fetch the relative BFF path, but it may import the
type from lib. App importing lib is the allowed direction.

## User Stories

1. As a maintainer, I want one result type, so that new forms cannot invent a different error surface.
2. As a maintainer, I want the type to live in lib, so that the lib to app dependency points one way.
3. As a user, I want API error strings verbatim, so that weak password and expired link notes stay exact.

## Implementation Decisions

- The new module lives in web lib. It exports the result type, call
  helpers for same origin JSON POST and PUT, and one detail parser.
- Error parsing keeps the shipped contract: the API's detail string
  surfaces verbatim, with a status fallback only when the body has no
  detail.
- Auth submit keeps its form data helper and delegates the transport
  and parsing. Register and the settings switch drop their local
  copies.
- The upstream resolver's switch read and landing resolve stay where
  they are. They are a server seam with different constraints.
- No form UI changes. States and copy stay as shipped.

## Testing Decisions

- The new module gets co-located vitest tests: call shape, verbatim
  detail, fallback detail, network failure.
- Existing consumer tests keep passing; their fetch stubs point at the
  same same origin paths.
- A layering test pins the direction: the new lib module imports
  nothing from the app directory.

## Out of Scope

- The server side upstream resolver's fetch path.
- Form component redesign.
- Retry, timeout, and refresh token behavior.
- Keeping password change's own success payload; only its error channel
  and type base move.

## Further Notes

- Source review: improve-codebase-architecture run of 2026-10-08,
  candidate 5. Five declarations of one shape and one inverted import
  are the friction.
- Layering rule of thumb: lib serves app. App serving lib is the smell
  this spec removes.
