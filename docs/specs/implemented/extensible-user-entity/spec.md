# Spec: Extensible user entity via extension tables

Status: implemented (PR #12).

Seam: the `User` model boundary and extension table attachment protocol.

## Problem Statement

The `User` model today holds authentication and account state in a
single table. When developers add features (such as user profiles,
metadata, or settings), they are tempted to add columns directly
to the `users` table.

Adding columns directly to `User` creates three problems:
1. It pollutes the core authentication model with domain-specific
   fields.
2. It causes schema merge conflicts when upstream updates the table.
3. It couples unrelated features to the authentication lifecycle.

## Solution

Enforce Pattern A (Extension Tables) across the codebase:
1. The core `User` model remains minimal. It contains only identity
   and credential fields (`id`, `email`, `hashed_password`,
   `is_active`, `created_at`, `updated_at`).
2. Domain features attach data using separate extension tables that
   reference `user_id`.
3. Provide a reference extension table: `user_profiles` (`user_id`,
   `display_name`, `avatar_url`, `bio`).
4. Keep the core user registration flow decoupled from extension
   tables. Extension records are created independently or through
   lifecycle handlers.

## User Stories

1. As a developer, I want the core `User` model locked to identity
   fields, so that authentication logic stays minimal and secure.
2. As a feature author, I want to store profile information in a
   dedicated `user_profiles` table, so that profile changes do not
   require altering the `users` table schema.
3. As a database maintainer, I want `user_profiles.user_id` to use a
   foreign key with `ON DELETE CASCADE`, so that deleting a user cleans
   up extension records automatically.
4. As an API consumer, I want endpoints to read and update profile
   data (`GET /api/users/{id}/profile`, `PUT /api/users/{id}/profile`), so
   that profile mutations do not complicate core user endpoints.
5. As an external developer, I want a documented pattern for building
   custom extension tables, so that downstream projects can add new
   entities without merge conflicts.
6. As a test writer, I want tests verifying that deleting a user
   cascades to their extension rows in a real Postgres test database.

## Implementation Decisions

- `apps/api/src/api/models/user.py` stays lean. No new columns are
  added to `User`.
- Create `apps/api/src/api/models/profile.py` defining `UserProfile`:
  `id`, `user_id` (ForeignKey to `users.id` with `ondelete="CASCADE"`,
  unique index), `display_name`, `avatar_url`, `bio`, `created_at`,
  `updated_at`.
- The relationship from `User` to `UserProfile` is modeled via standard
  SQLAlchemy 1:1 relationship with `uselist=False`.
- Create Pydantic schemas in `apps/api/src/api/schemas/profile.py`:
  `ProfileRead`, `ProfileUpdate`, `ProfileCreate`.
- Create router endpoints in `apps/api/src/api/routers/profiles.py`
  mounted under `/api/users/{user_id}/profile`.
- Create a dedicated Alembic migration adding the `user_profiles`
  table.
- GET on an existing user with no profile returns 404
  `{"detail": "profile not found"}`. Pinned by ticket 02 tests.
- PUT is replace: a partial body resets omitted fields to null.
  Pinned by test.

## Testing Decisions

- Test user creation succeeds without creating a profile record.
- Test profile creation, update, and retrieval for an existing user.
- Test attempting to create a profile for a non-existent user raises a
  not-found error.
- Test deleting a user automatically removes the associated profile row
  via foreign key cascade.
- Tests run against the test Postgres database.

## Out of Scope

- Polymorphic inheritance or single-table inheritance.
- Modifying authentication tokens, session cookies, or passwords.
- Moving `User` to a separate package (handled in later packaging specs).

## Further Notes

- `docs/specs/implemented/extensible-user-entity/spec.html` visualizes the table
  composition and separation.
