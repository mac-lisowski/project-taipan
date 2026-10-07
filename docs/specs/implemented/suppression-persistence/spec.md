# Spec: Suppression persistence

Status: planned.

Seam: the suppression lookup behind `GuardedEmailSender`.
A Postgres store replaces `MemorySuppressionStore`.
A signed webhook route feeds bounce reports into it.

## Problem Statement

Suppression state lives in process memory.
A restart wipes the do-not-send set and all counters.
A hard-bounced address becomes sendable again.
Two app instances hold divergent sets.
Rate bounds are lifetime counters in one process.
A restart reopens abuse limits.
The email spec requires suppression state in app persistence.
That requirement is unmet.

## Solution

Add one Postgres-backed store behind a new `SuppressionStore` port.
Wire it in the mail composition root in place of the memory store.
Persist send-rate counters through the same port.
Add one signed webhook route.
It maps provider bounce events to `record_bounce`.
No sender interface change.
No template change.

## User Stories

1. As an operator, I want a suppressed address to stay suppressed
across restarts, so that reputation stays clean.
2. As an operator, I want all app instances to share one set,
so that scaling out does not resend to bounced addresses.
3. As an operator, I want soft bounces counted persistently,
so that the third strike still suppresses after a restart.
4. As an operator, I want rate bounds enforced from shared counts,
so that a restart does not reopen abuse limits.
5. As an operator, I want bounce reports to feed suppression
automatically, so that no human copies addresses by hand.
6. As a developer, I want the memory store kept for tests,
so that unit tests stay fast with no database.
7. As a developer, I want one conformance suite proving both stores
behave the same, so that the swap cannot drift semantics.

## Implementation Decisions

- One new table `email_suppressions` owns the do-not-send set.
Address is the natural key: `address TEXT PRIMARY KEY`.
The app lowercases and strips before write, matching `_key`.
Columns: `reason TEXT NOT NULL` with
`CHECK (reason IN ('hard','soft-limit','complaint'))`,
`soft_bounces INTEGER NOT NULL DEFAULT 0`,
`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`,
`updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- One new table `email_send_counters` owns rate state:
`recipient TEXT NOT NULL`, `template TEXT NOT NULL`,
`sent_count BIGINT NOT NULL DEFAULT 0`,
`PRIMARY KEY (recipient, template)`.
Per-recipient totals derive from `SUM` over templates.
Only `SENT` results increment.
Counts are lifetime cumulative with no reset,
preserving current code semantics.
- One new table `email_webhook_events` dedupes intake:
`event_id TEXT PRIMARY KEY`,
`received_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
The route calls `record_bounce` with the provider event id;
repeats are no-ops returning the same outcome.
Unit tests use an in-memory seen-set double.
One replay test runs against Postgres on the `app_test` database.
- One new `SuppressionStore` port declares the seam,
five methods total; all persistence crosses the port:
`is_suppressed(address)`, `suppress(address)`,
`record_bounce(address, kind, event_id=None)` returning
suppressed-now (HARD and COMPLAINT suppress, SOFT counts
toward `MAX_SOFT_BOUNCES`, repeat event id is a no-op),
`send_allowed(template, recipient)` returning None
or a reject reason, `note_sent(template, recipient)`
called only on `SENT` with a bounds re-check inside.
Callers learn outcomes, never counters.
The memory store implements all five with dicts.
The guard constructor re-hints from the concrete class
to the port.
Rate dicts leave the guard; all state crosses the port.
- Soft-bounce counting stays atomic:
one `UPDATE ... RETURNING` per report.
It suppresses when the count reaches `MAX_SOFT_BOUNCES` (3).
Counter increments stay atomic the same way.
No read-modify-write anywhere.
- `BounceKind` gains `COMPLAINT`.
`record_bounce` maps it to `suppress()` with reason `'complaint'`.
- The Postgres store takes the app session factory.
Each method opens one short session.
`build_email_sender` in `apps/api/src/api/mail.py` gains
an optional factory parameter.
`main.py` passes the app `SessionLocal`.
Wiring changes in that one call only.
- One webhook route `POST /api/email/webhooks/resend`
receives provider events.
It verifies the Svix signature headers
(`svix-id`, `svix-timestamp`, `svix-signature`)
against a new `MailConfig.resend_webhook_secret`
(empty default, documented in `.env.example`).
Bad signature or stale timestamp returns 401
with no state change.
Mapping: hard bounce records `HARD`,
soft bounce records `SOFT`,
complaint records `COMPLAINT`,
all other event types are ignored.
- Suppression never expires and has no unsuppress path.
Ops remove a row by hand when truly needed.
- Schema ships as one Alembic migration
in `apps/api/alembic/versions/` via `uv run db-revision`,
reviewed before apply per house rule.
Never edit an applied migration.
- This table is keyed by address, not by user id,
so the extensible-entities rule does not apply.
No core model changes.
- Send transport and webhook verify use the official `resend` SDK.
Vendor failure text never reaches reasons or logs.

## Testing Decisions

- Existing suppression tests become a conformance suite
parametrized over both stores.
The Postgres leg runs on the `app_test` database.
One behavior per test: suppress short-circuits send,
third soft bounce suppresses,
counters increment on sent only,
bounds reject with retryable reasons,
values 100 per recipient and 50 per template hold.
- Webhook tests use a stubbed signer.
Valid signature maps each event kind to the right store call.
Bad signature returns 401 with no state change.
Unknown event kinds are ignored.
Replayed event ids are skipped.
- Wiring test pins the composition root.
With a session factory present, `build_email_sender`
returns a guard holding the Postgres store.
Tests keep the memory store.
- After editing tests, run the structural test check first,
then the test smell review.
A test that cannot fail is removed.

## Out of Scope

- Inbound mail, replies, and parsing.
- Per user mail preferences beyond suppression.
- Bounce analytics dashboards.
- Vendor migration beyond the Resend adapter.
- Backfill of historical bounces from before this ships.
- Support read tooling for suppressed status.
- Suppression expiry or self-serve unsuppress.
- Webhook secret rotation (single secret, rotate via redeploy).
- Counter reset policy (counts are lifetime by decision).

## Further Notes

- The companion visual lives beside this file in spec.html.
It shows the store swap and the webhook feed.
- This closes the persistence gap recorded when the email
delivery spec moved to implemented.
Activation and reset caller flows still belong
to the registration and password-reset specs.
