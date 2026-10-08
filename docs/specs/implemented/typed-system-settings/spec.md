# Spec: Typed system settings

Status: implemented.

Seam: the system settings module speaks in typed accessors. The key
value encoding becomes private. Callers never see raw strings.

## Problem Statement

The settings module exposes raw get and set over key value strings.
One typed key exists today, registration_enabled. The true and false
string encoding is part of the public interface, so every future
setting re-decides it. Nothing stops a caller from bypassing the typed
pair and writing raw values.

## Solution

The raw pair becomes private. The module's interface is typed
accessors only, one pair per setting. Each pair owns its key name, its
encoding, and its default. Adding a setting means adding a typed pair.
The key value table stays the storage shape.

## User Stories

1. As a maintainer, I want typed accessors only, so that no caller can write a malformed value.
2. As a maintainer, I want the encoding private, so that a future encoding change touches one file.
3. As an operator, I want the registration switch to keep its behavior, so that this refactor changes nothing I can see.

## Implementation Decisions

- get and set become private helpers of the module. The public
  interface is one accessor pair per setting.
- registration_enabled keeps its contract: missing key reads false,
  values stored as true and false strings, upsert over the key.
- A future setting arrives as a new typed pair with its own default.
  No generic string door stays open.
- The table, migration, router, and guard are untouched. This is an
  interface shrink, not a storage change.

## Testing Decisions

- Existing settings tests keep passing unchanged.
- A module test pins that the public surface exposes no raw string
  accessors, by importing the module and asserting its exports.
- The round trip and default tests move to the typed pairs if they are
  not already there.

## Out of Scope

- New settings beyond the registration switch.
- Caching or change notifications.
- Any change to the settings API routes or the web page.

## Further Notes

- Source review: improve-codebase-architecture run of 2026-10-08,
  candidate 4. The design review called the raw pair a shallow flank
  with no external caller.
- Deletion test: deleting the raw pair loses nothing today. That is the
  signal to make it private until a real second need shows.
