# Spec: Decide the seam for encrypted fields

Seam: none yet. This spec exists to choose one. The deliverable is
an ADR, not code.

## Problem Statement

The infisical-kms spec named the next consumer: envelope encryption
of Postgres fields, so the database stores only ciphertext. Where
that conversion lives is an open fork. A column-level
`TypeDecorator` puts encryption inside the ORM and makes the
repository layer deletable. Repository-owned conversion makes
repositories earn their depth. Picking after implementation starts
means rework either way. The repository layer currently fails the
deletion test, so its fate rides on this decision.

## Solution

Write `docs/adr/` ADR-0001 choosing the seam, backed by a throwaway
prototype of the preferred shape so the ADR cites verified
behavior, not guesses. The ADR records both options, the criteria,
and the reason the loser lost, so future reviews do not re-suggest
it.

## User Stories

1. As a developer, I want a decided seam for encrypted fields, so
   that the encryption feature spec starts without an open design
   fork.
2. As a reviewer, I want the rejected option recorded with its
   reason, so that no future architecture review re-suggests it.
3. As a developer, I want a throwaway prototype of the winning
   shape, so that the ADR cites verified behavior.
4. As a developer, I want the decision to account for query
   behavior, so that "cannot filter on ciphertext" is an explicit
   accepted cost, not a surprise.
5. As a maintainer, I want the ADR under `docs/adr/`, so that it
   survives scratch state and session context.
6. As a developer, I want the decision to state what happens to
   `BaseRepository`, so that the shallow-layer question is closed.
7. As a developer, I want the decision to state how tests cross
   the chosen seam, so that the test surface is designed now.
8. As an operator, I want key-id sourcing decided (config vs
   column), so that rotation semantics are part of the record.

## Implementation Decisions

- Create `docs/adr/` with ADR-0001: "Seam for encrypted model
  fields". Status: accepted when the prototype confirms the shape.
- The two options under evaluation:
  - Option A: column-level `TypeDecorator`. Encryption rides the
    ORM. Every read/write converts transparently. Repositories
    become deletable; the deletion test then favors removing them.
  - Option B: repository-owned conversion. The repository module
    encrypts on write and decrypts on read. Repositories become
    the deep module that owns ciphertext handling.
- Decision criteria, evaluated by the prototype:
  - Locality: where does ciphertext logic concentrate, and can a
    caller bypass it?
  - Test surface: can encryption be verified through the seam
    without HTTP, and with a stubbed `Cipher` port?
  - Query limits: equality filters, ordering, and joins on
    ciphertext columns.
  - Migration shape: how existing plaintext rows would rewrap
    under each option.
  - Key rotation: where the key id is read, and how a versioned
    key changes existing rows.
- The prototype is throwaway: it lives in `.scratch/` or is
  deleted after the ADR is written. It proves one encrypted column
  round-trips through the live `Cipher` port.
- No production code changes in this spec. The output is the ADR
  plus a decision on the repository layer's fate.

## Testing Decisions

- No production code ships, so no test suite additions.
- Mechanical verification for the DoD: the ADR file exists, names
  both options, states criteria, cites the prototype outcome, and
  answers the repository-fate question.
- The prototype itself must round-trip real bytes through the
  live Infisical instance, reusing the existing KMS test
  conventions (skip when instance or token missing).

## Out of Scope

- Actually encrypting any model field in production code.
- Migrations that rewrap existing data.
- Blind indexes, searchable encryption, key rotation sweeps.
- The field-encryption feature spec itself; this only picks its
  seam.

## Further Notes

- Candidate 4 (Speculative) from the architecture review. It is
  deliberately a decision spec: the wrong outcome is not "pick A
  over B" but "let the feature spec improvise the seam".
- `docs/specs/encryption-seam/spec.html` visualizes the two
  candidate seams.
