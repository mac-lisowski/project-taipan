# Spec: Email delivery package

Status: planned.

Seam: one email delivery package with a single sender interface. All app code sends mail through it. A Resend adapter serves prod. A fake adapter serves local dev and tests.

## Problem Statement

Auth flows need mail. Activation and resets send tokens by mail. Login keeps the existing password flow and sends no mail. Today there is no shared seam for sending. Each caller would wire its own client. That spreads keys, templates, and failure modes. Local dev has no safe story. Tests would hit the network or skip mail asserts. The app needs one place that owns sending, templates, and dev safety.

## Solution

Add one reusable email delivery package. It exposes a small sender interface with one send call. Callers name a template and pass data. The package renders and sends. A Resend adapter handles prod delivery. A fake adapter captures mail in local dev and tests. Each email type gets its own template. Bounce handling stays thin. Delivery events are logged. Hard bounces mark the address as do-not-send. No inbound mail handling ships now.

## User Stories

1. As a new user, I want an activation mail after sign up, so that I can verify my address.
2. As a returning user, I keep the existing password login, so that no second sign in path exists.
3. As a user who forgot access, I want a reset mail, so that I can regain my account.
4. As a user, I want mail that shows my app name and a clear action link, so that I trust it and know what to do.
5. As a user, I want short lived single use links, so that a leaked mail does not stay valid.
6. As a user, I want to land on the dashboard after login or activation, so that I start from one known place.
7. As a developer, I want one sender interface for all mail, so that I never wire a mail client in a route.
8. As a developer, I want one template per email type, so that copy changes touch one small unit.
9. As a developer, I want typed template data per email, so that a missing field fails fast before send.
10. As a developer, I want a fake adapter in local dev, so that I can test flows with no real sends.
11. As a developer, I want the fake adapter to list captured mail, so that I can assert subjects and links in tests.
12. As a developer, I want prod keys kept in server config only, so that the web client never sees them.
13. As an operator, I want Resend as the single prod adapter, so that there is one vendor to monitor.
14. As an operator, I want send failures logged with template name and cause, so that I can triage fast.
15. As an operator, I want hard bounces to suppress future sends to that address, so that reputation stays clean.
16. As an operator, I want soft bounces retried a small bounded number of times, so that brief issues do not lose mail.
17. As a maintainer, I want sessions to reuse the existing sessions table pattern, so that auth state stays in one model.
18. As a maintainer, I want token rules shared with auth, so that mail links stay single use, hashed at rest, and short lived.
19. As a support agent, I want to know if an address is suppressed, so that I can explain missing mail.
20. As a user with a typo in my address, I want no account leak in the response, so that my privacy holds.

## Implementation Decisions

- One new email delivery package owns all sending. It exposes a sender interface with a single send operation. All app code crosses this seam. No direct vendor calls exist outside it.
- The sender takes a template name plus typed data plus recipient. It returns a typed result of sent, suppressed, or failed with a reason. Callers map the result to user facing behavior.
- One template per email type. Activation and reset each own a template with fixed subject and body shape. Shared layout such as brand header and footer is composed inside the package. No generic free form send exists. No login link mail exists. Login stays on the existing password flow.
- Templates use the Jinja2 engine. Python native rendering keeps sends free of a Node step. One template file per email type lives in the package. Shared brand parts are partials composed inside the package.
- Template data is validated before render. Missing or bad fields reject the send without network use. Render output stays plain and small.
- A Resend adapter implements the sender interface for prod. It reads its key from server config at startup. It fails closed when the key is absent. It never logs the key or full token values.
- A fake adapter implements the same interface for local dev and tests. It stores sent mail in memory and exposes a read and clear operation. It never touches the network. Dev flows render the same templates through it.
- Adapter choice happens once at composition time from config. App code receives the sender interface only. It never knows which adapter is active.
- Token handling stays with auth, not mail. Tokens in mail links are single use. Only hashes persist at rest. Expiry is short. The mail package treats link strings as opaque data.
- After login or activation the web lands on the dashboard route at /dashboard. The mail package does not own routing. It only carries the link that starts the flow.
- Session handling reuses the existing sessions table pattern. The mail package creates no session state. Auth creates sessions as today.
- Bounce stance is thin. The package logs delivery outcomes. Webhook or poll based bounce reports feed a suppression set keyed by address. Hard bounce adds suppression. Soft bounce retries a small bounded count, then stops. Suppressed addresses short circuit to a suppressed result with no vendor call.
- Suppression checks run before render or send. Suppression state lives with app persistence, not in the mail package memory. The package defines the lookup interface. The app wires the store.
- Rate of sends is bounded per recipient and per template. Excess requests are rejected with a retryable reason. This limits abuse through resend endpoints.
- No inbound mail, no attachment pipeline, no bulk campaigns. Outbound transactional mail only.

## Testing Decisions

- Unit tests drive the sender interface with the fake adapter. They assert template choice, subject, recipient, and link presence. They assert suppressed short circuit with no vendor call.
- Template tests pin one case per email type. They assert render with valid data. They assert fast reject with missing data. They assert no token or key material leaks into logs.
- Adapter tests pin the Resend mapping with a stubbed transport. They assert auth header use from config. They assert fail closed with no key. They assert failure mapping to the typed result. No test hits the real vendor.
- Bounce tests assert hard bounce adds suppression. They assert repeat sends to a suppressed address return suppressed. They assert soft bounce retries stop at the bound.
- Auth flow tests use the fake adapter end to end. They request activation or reset mail, read the captured link, and complete the flow. They assert landing on the dashboard route after login or activation.
- Token rule tests live with auth. They assert single use, hash at rest, and short expiry. Mail tests only assert the link is present and opaque.
- After editing tests, run the structural test check first, then the test smell review. A test that cannot fail is removed.

## Out of Scope

- Inbound mail, replies, and parsing.
- Bulk mail, newsletters, and marketing templates.
- Attachments and rich media builders.
- Vendor migration beyond the Resend adapter.
- Full bounce analytics dashboards.
- Password storage changes or session format changes.
- React Email components and Node based render steps.
- Per user mail preferences beyond suppression.

## Further Notes

- This spec follows the assignment contracts directly. It defines one package seam with a Resend adapter. It defines one template per email. It uses a fake adapter for local dev. Bounce stance stays thin. Tokens stay single use, hashed at rest, and short lived. The web lands on the dashboard after login or activation. Sessions reuse the existing table pattern.
- The companion visual lives beside this file in spec.html. It shows the seam, the adapters, and the test seam.
