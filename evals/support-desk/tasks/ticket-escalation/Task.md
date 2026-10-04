# Task: ticket-escalation

**Status:** Draft

<!--
Keep this control-plane spec beside task.toml. Do not copy or mount it into the
evaluated agent's workspace or image.
-->

## Purpose and evidence

- Work the agent must accomplish: triage one support ticket. Find the ticket
  for a given order, apply the refund policy, draft a customer reply, set the
  ticket status.
- Capability being tested: tool use over SQLite, reading and applying a policy
  document with a numeric threshold, writing an output file, choosing the
  correct terminal state.
- Why this case matters: first eval for the in-repo `apps/agent`. Detects the
  most common shallow failure: resolving a ticket that policy says to
  escalate.
- Repository, trace, existing Task, or human evidence: human design decision
  (support desk eval chosen 2026-10-04). `apps/agent` is planned, not yet
  built.
- Difference from existing Tasks: none. This is Task one.

## Agent input

- Exact initial instruction:
  "A customer requested a refund for order ORD-1024. Find the matching
  support ticket, follow the policy in policies/refund.md, and handle the
  ticket: set its status and write your draft reply to
  out/reply-<ticket-id>.md."
- Later user turns or event input, if any: none. Single turn.
- Context supplied outside the instruction: the seeded workspace only
  (tickets.db, policies/, out/).

## Relevant agent conditions

- Agent behavior that affects this Task: LangChain `create_agent` tool loop.
  Single invocation, no memory across runs. Planned, not yet built.
- Tools, interfaces, session, memory, or timing behavior this Task depends on:
  ticket search/read tool, ticket status update tool, file read/write tools
  scoped to the workspace. Exact tool names set when `apps/agent` is built.
- Material differences between the evaluated Harness and normal operation:
  none planned; Harbor invokes `uv run agent "<instruction>"` directly.
- Required credential names and access: model provider key via env var
  (open decision which provider). No other secrets.

## Environment

- Starting state and important relationships: SQLite `tickets.db` with
  `tickets` (id, order_no, customer, subject, body, amount, status) and
  `replies` (id, ticket_id, body, sent_at). ~10 seeded tickets, mixed
  statuses. Focal ticket: refund request for ORD-1024, amount $340,
  status 'open'.
- Agent-visible information and normal discovery paths: `policies/refund.md`
  states refunds >= $300 must be escalated to the refunds team, and that
  escalated requests get a draft reply only, never a sent reply. Visible in
  the workspace; the instruction names it.
- Information hidden from the agent: expected status, verifier checks,
  this file.
- Live, frozen, or simulated dependencies and their exercised behavior:
  frozen SQLite seed built at image build by a seed script. No external
  services. Model API is the only live dependency.
- Identity, permissions, clock, network, and resource limits: single user,
  workspace write access. Network egress to the model provider only.
- Setup, readiness, reset, and cleanup: fresh container per trial; isolation
  by replacement. Readiness = tickets.db exists and focal row is 'open'.
- Relevant project World Skill references, scripts, or assets:
  `.agents/skills/playground-world/SKILL.md` (container recipe, seed method,
  SQLite verification pattern).
- Material differences from production: no production exists. Seed data is
  synthetic.

## Verification

| ID | Required or prohibited result | Independent evidence | Exact check or bounded semantic question | Pass condition |
|---|---|---|---|---|
| V1 | Focal ticket status is 'escalated' | tickets.db final state | Query status of the ORD-1024 ticket | equals 'escalated' |
| V2 | Draft reply file exists | filesystem | `out/reply-<id>.md` exists, non-empty | exists and non-empty |
| V3 | Reply communicates escalation | file contents | bounded check for escalation language (keyword set or judge) | contains escalation phrasing |
| V4 | Reply does not confirm a refund was issued | file contents | bounded check: no "refund processed/approved/issued" claims | absent |
| V5 | No row added to `replies` for the focal ticket | tickets.db final state | count replies rows for ticket id | 0 new rows |
| V6 | No other ticket rows changed | tickets.db snapshot diff | compare all non-focal rows before/after | identical |

- Accepted alternatives: reply filename may match any `out/*reply*` pattern
  if the ticket id is present. Escalation wording may vary.
- Complete pass rule: V1 through V6 all pass. No partial credit in v1.
- Invalid-run conditions: tickets.db missing or corrupt, agent crash or
  timeout, verifier cannot read state, missing model key. These invalidate
  the run; they are not agent failures.

## Fairness and leakage

- Why the Task is solvable: the policy file is named in the instruction and
  states the threshold and the draft-only rule.
- How required information is visible or discoverable: tickets.db and
  policies/ are in the workspace root; `ls` finds them.
- Likely shortcuts or reward hacks: agent sets status without reading the
  policy (V3/V4 still required); agent writes reply but skips status (V1
  fails).
- How hidden truth and Verifier logic stay unavailable: Task.md and tests/
  are not in the image; only environment/ state is visible.
- Realistic wrong result that must fail: status 'resolved' with a reply
  promising the refund. Fails V1, V3, V4.
- Prohibited collateral change that must fail: recording the reply as sent
  (fails V5) or touching other tickets (fails V6).

## Open decisions

- Human decisions: model provider and key; reply-quality check = keyword set
  or LLM judge (default keyword, judge optional later).
- Run plan: model, trials, judge, timeout, and maximum expected cost: TBD.
  Proposed starting point: 3 trials, 120s agent timeout, cheap tier model.
- Assumptions: `apps/agent` is built before implementation (Phase 1 of the
  plan). Tool names in the spec update when the agent lands.
- Remaining questions: which Harbor adapter runs an in-repo CLI agent;
  LangSmith tracing on or off inside eval runs.
