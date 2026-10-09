---
name: write-pseudocode
description: Write decision-pinning pseudocode for specs and tickets. Use when a spec section, ticket plan, or review needs control flow pinned precisely (state machines, reducers, branching, retries, ordering). Not for wiring, CRUD, or boilerplate - name the shape instead.
---

# Write Pseudocode

Pseudocode pins a logic decision so prose cannot drift. Use it where
control flow IS the decision: branching, state transitions, loop
bounds, retry and ordering rules. It lives in spec Implementation
Decisions and ticket Implementation plans, in place of a prose
paragraph that would list the same branches vaguely.

## Format

- One action per line. Indent 4 spaces per level.
- Declare inputs and output on the first line:
  `PROCEDURE name(input, input) -> output`.
- Control words uppercase, only from this set:
  `SET ... TO`, `IF`, `ELSE IF`, `ELSE`, `FOR EACH ... IN` (closes
  `END FOR`), `WHILE`, `LOOP`, `RETURN`, `CALL`, `THROW`, `BREAK`,
  `CONTINUE`, `AND`, `OR`, `NOT`, `IN`, `END IF`, `END WHILE`,
  `END LOOP`, `END PROCEDURE`.
- Conditions use plain math (`=`, `>`, `<=`) or words; never `==`,
  `:=`, or `<-`. Assignment is only `SET name TO expression`.
- Language-neutral. No semicolons, braces, imports, or real API
  calls. Use domain glossary nouns and verbs.
- Every branch explicit: each `IF` gets an `ELSE` or a stated
  fall-through. Error paths are lines, not comments.
- Cap a block at ~15 lines. Longer means split: extract a named
  `PROCEDURE` and `CALL` it.

## Process

1. Outline the high-level steps first: numbered, one per line.
2. Expand each step into pseudocode.
3. Stop when a reader could hand-implement with no design decision
   left open. Earlier is too vague; later is uncompiled code.

## Example

```
PROCEDURE load_users_page(query, status, page, page_size) -> UserPage
    IF page_size IN 10, 25, 50
        SET size TO page_size
    ELSE
        SET size TO 10
    END IF
    SET total TO count of users matching query AND status
    SET last_page TO ceil(total / size), minimum 1
    IF page > last_page
        SET effective_page TO last_page
    ELSE
        SET effective_page TO page
    END IF
    SET offset TO (effective_page - 1) * size
    SET rows TO matching users, newest first, skipping offset rows, taking size
    RETURN rows, total, effective_page, size
END PROCEDURE
```

This is the level of detail expected: every branch written, no syntax
borrowed from a language, each line a decision a reader must not
re-guess.

The same logic written as pseudo-TypeScript is wrong. It drifts with
the codebase, borrows irrelevant detail (types, imports, syntax), and
hides branches in operators:

```
async function load(q, s, p, ps) { const rows = await db... } // no
```

## Self-check

Read the block back and attack it:

- Ambiguity: could two implementers produce observably different
  behavior? Tighten until no.
- Hidden decisions: does a verb like "handle", "process", "validate"
  hide the actual rule? Expand that line or name what it checks.
- Branches: every `IF` has an `ELSE` or explicit fall-through; every
  error path is written.
- Staleness: any real filename, endpoint, or API call? Replace with a
  domain verb. Pseudocode outlives the code it names.
- Judgment leak: does it dictate what the implementer should own
  (field names, helper structure, comments)? Cut back to the
  decision.

## Contract

Pseudocode is a contract for logic, not literal code. An implementer
preserves its control flow and branch coverage in the real types, and
is free to rename, restructure helpers, and pick syntax. A reviewer
checks branch coverage against the block, not surface wording.
