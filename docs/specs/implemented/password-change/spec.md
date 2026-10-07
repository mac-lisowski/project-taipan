# Spec: Password change

Status: implemented (PR #34).

Seam: a password-change module owns the change rules over an
injected session. The shared email-delivery seam owns the change
notice with a Resend adapter. Routers stay thin.

## Problem Statement

Signed-in users cannot change their own password. There is no self-serve flow on the account page. Users who fear a leaked password must ask an admin or wait for a reset flow. The app needs a safe change flow with clear rules and safe session handling.

## Solution

Add a change password action on the account page. The user enters the current password and a new password twice. The API checks the current password, checks the new password rules, then stores a new hash. Session handling reuses the existing sessions table pattern. Other sessions stay valid or end per the chosen rule, and the choice is stated in one place.

## User Stories

1. As a signed-in user, I want to change my password from the account page, so that I can react fast when I fear a leak.
2. As a signed-in user, I want to enter my current password first, so that no one can take over my account from an open laptop.
3. As a signed-in user, I want to type the new password twice, so that a typo does not lock me out.
4. As a signed-in user, I want clear password rules before I submit, so that I do not guess what is valid.
5. As a signed-in user, I want a clear error when the current password is wrong, so that I know what to fix.
6. As a signed-in user, I want a clear error when the new password is too weak, so that I can pick a stronger one.
7. As a signed-in user, I want a clear success note after the change, so that I know it worked.
8. As a signed-in user, I want to stay signed in on this device after the change, so that I am not kicked out by my own action.
9. As a signed-in user, I want to know if other devices stay signed in, so that I can act if I fear theft.
10. As a signed-in user, I want the same rules each time I retry, so that the flow feels fair and stable.
11. As a signed-out visitor, I want no access to this action, so that only the account owner can change the password.
12. As a support agent, I want no plain passwords in logs or errors, so that user secrets stay safe.
13. As a developer, I want one domain seam for the change logic, so that rules live in one place and not in the router.

## Implementation Decisions

- New password change module inside the domain layer with a small interface over an injected session and injected helpers. It owns the rules and returns typed domain errors.
- The HTTP layer stays thin. It maps domain errors to status codes and owns request shape checks only.
- Current password check uses the same hash verify helper as login. No new hash scheme is added.
- New password rules live in one shared checker. The web and the API use the same rule set. Rules cover least length and a simple strength bar.
- Session handling reuses the existing sessions table pattern. The change writes through the same store seam. The spec keeps the current device session valid and ends or keeps other sessions per one stated policy.
- Email notice about the change goes through the one shared email-delivery seam with the Resend adapter. No direct mail calls from this feature.
- No token is issued by this flow. Token rules on single use, hashed rest state, and short life stay in force for reset flows and are not bent here.
- After login or activation the web still lands on the dashboard. This flow returns the user to the account page with a success note.
- Core user identity stays small. No feature columns land on the core user record. Change metadata, if stored, lives in a side table or log linked by user id.

## Testing Decisions

- Good tests call the domain module with a real test session and assert on pass or fail. They do not need HTTP.
- New module tests: wrong current password fails; weak new password fails; same-as-old fails; valid change stores a new hash; old password stops working; new password verifies.
- Session tests: current device session stays valid; other sessions follow the stated policy; signed-out calls are refused.
- HTTP tests pin the error map only: wrong current maps to one client error; weak new maps to one client error; signed-out maps to denied.
- UI tests pin the form states: rules shown; mismatch of the two new fields blocks submit; success note shows after a good change.
- After editing tests, run the structural check tool first, then the test smell review. A test that cannot fail is cut.

## Out of Scope

- Forgot password and reset by mail link.
- Admin set password for another user.
- Two factor changes or recovery codes.
- Password history store past one check.
- Strength meter design beyond a simple bar.

## Further Notes

- This flow complements reset flows but stays apart from them. Reset uses mailed tokens. Change uses a live session plus the current password.
- The module and seam diagram plus the test seam note live in the visual report next to this file at spec.html.
