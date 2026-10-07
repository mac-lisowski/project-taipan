# Spec: Password reset

Status: implemented (PR #37).

Seam: a password-reset module owns token rules over an injected
session. An email-delivery module owns all mail sending with a
Resend adapter. Routers stay thin.

## Problem Statement

Users who forget a password have no way back in. There is no
request link flow and no token reset flow. Any reset built ad hoc
would leak account existence, store raw tokens, or leave old
sessions live. Mail sending has no shared seam, so each feature
would wire its own sender and drift.

## Solution

A forgot-password flow takes an email and always gives the same
reply. It never shows if the account exists. When the account
exists, it mints a single-use reset token, stores only its hash
with a short expiry, and sends a link through the email-delivery
seam. A reset-password flow takes the token link plus a new
password, sets the new hash, burns the token, revokes all user
sessions, and logs the user in. The web then lands on
/dashboard.

## User Stories

1. As a locked-out user, I want to request a reset link by email, so that I can get back in.
2. As a locked-out user, I want the same reply whether or not my email is known, so that no one can probe for accounts.
3. As a user, I want a reset link that works once and dies fast, so that a leaked link has little value.
4. As a user, I want my new password set from the token link, so that reset takes one step.
5. As a user, I want all old sessions dead after reset, so that a lost device loses access.
6. As a user, I want to land logged in after reset, so that I do not log in twice.
7. As a user, I want to land on /dashboard after reset login, so that login and reset agree.
8. As a user, I want a clear error on a bad or used token, so that I know to ask again.
9. As a user, I want a clear error on a weak new password, so that I can fix it at once.
10. As a developer, I want token rules in one module, so that expiry and single use live in one place.
11. As a developer, I want all mail sent through one email-delivery seam, so that no feature wires its own sender.
12. As a maintainer, I want reset tokens stored hashed at rest, so that a read of the store gives nothing usable.
13. As a maintainer, I want session cleanup to reuse the sessions table pattern, so that reset and login share one truth.
14. As a test runner, I want the flows tested at the module seam with a fake adapter, so that tests need no real mail.

## Implementation Decisions

- New password-reset module: it exposes request and reset acts over an injected session. It returns plain results and raises typed domain errors. It holds no mail and no HTTP logic.
- Request act: look up the user by email in silence. For a known user, mint a random token, store its hash with issue time and short expiry, then call the email-delivery seam with the link. For an unknown email, do nothing and return the same result.
- Reset act: hash the given token and match it to a live unused record. Reject missing, used, or past-expiry tokens with a typed error. On success, set the new password hash, mark the token used, and revoke all sessions for that user through the sessions pattern. Then mint a fresh login session.
- Token shape: random, single-use, hashed at rest, short expiry. Raw tokens live only in the link and in memory during the act. The store never holds a raw token.
- Email-delivery seam: the one shared mail seam takes a template name plus typed data plus recipient. A Resend adapter backs it in production. A fake adapter serves tests and local runs. All reset mail goes through this seam. No other sender is added.
- Session handling: reset reuses the existing sessions table pattern (raw token in cookie, hash in store, TTL from config). Revoke-all deletes every row for the user before the new login session is minted.
- Routers stay thin: they map request bodies, call the module acts, map typed errors to status codes, and set or clear the session cookie. They hold no token rules.
- Web flow: forgot form posts an email and shows one neutral note. Reset form takes the token from the link plus the new password, then lands on /dashboard on success, matching login and activation.
- Password policy: the same hasher and strength rule used at registration apply here. No second policy is added.

## Testing Decisions

- Good tests call the password-reset module with a real test session and a fake adapter. They assert on results and raised errors. They do not touch HTTP or real mail.
- Request tests: known email queues one link mail and stores a hash, never a raw token. Unknown email sends nothing yet returns the same result.
- Reset tests: a live token sets the new hash and burns the token. Second use fails. Past-expiry fails. Unknown token fails. Reset revokes all prior sessions. A weak password is rejected and the token stays live.
- Mail seam tests: the fake adapter records sends; reset tests assert one send per known-email request and zero sends for unknown emails. The Resend adapter is tested with a stubbed transport only.
- HTTP tests pin the thin mapping: neutral reply for both known and unknown emails; bad token maps to its error status; success sets the session cookie and points at /dashboard.
- Prior art: module tests use the real test session convention with skip when the store is down. After editing tests, run the structural check then the smell review.

## Out of Scope

- Change of password while logged in.
- Login, registration, or activation changes.
- New mail templates beyond the reset link.
- Rate limit or captcha on the request flow.
- Token refresh, remember me, or multi device views.

## Further Notes

- This spec pairs with the email-delivery seam: reset is its first caller and the Resend adapter lands with it.
- After login or activation the web lands on /dashboard, and reset matches that rule.
- See spec.html beside this file for the module and seam map plus the test seam note.
