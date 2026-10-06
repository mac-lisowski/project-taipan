---
name: to-spec
description: "Turn the current conversation into a spec file under docs/specs/: no interview, just synthesis of what you've already discussed."
disable-model-invocation: true
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user; just synthesize what you already know.

Specs are saved as files in `docs/specs/planned/<slug>/spec.md` and
move to `docs/specs/implemented/<slug>/` when the spec ships. There is no
issue tracker; tickets are scratch files under `.scratch/<slug>/`
(gitignored) and implement-spec reads the files directly.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then save it to
`docs/specs/planned/<slug>/spec.md` where `<slug>` is a short kebab-case name
for the feature. Tell the user the file path. Tickets (created later
by to-tickets) go in `.scratch/<slug>/issues/`, not in docs.

4. Write the visual artifact: `docs/specs/planned/<slug>/spec.html` beside
`spec.md`. Every spec gets one. It is a durable, committed artifact,
not a temp file - it is what a reader opens to understand the spec's
shape before reading prose. Rules:

- Self-contained HTML. Tailwind and Mermaid via CDN. No build step,
  no local assets.
- STE100 prose (repo rule). No em dashes.
- Required visuals: the module/seam shape (Mermaid for graph-shaped
  relationships), a before/after depth comparison when the spec
  restructures existing code (hand-made CSS bars or divs work well),
  and the test seam: what tests cross, what they assert.
- Keep it under ~150 lines. It is a map, not a second copy of the
  spec.
- Reference it from `spec.md` Further Notes so the pair stays linked.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
