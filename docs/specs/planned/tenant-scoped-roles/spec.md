# Spec: Tenant-Scoped Roles and the System Owner Role

Status: planned.

Seam: two existing seams, no new ones. The HTTP seam drives setup, login,
`/me`, and `/users` through the app test client. The migration seam runs
real alembic upgrades against a scratch database. Both seams already exist.

## Problem Statement

The first user created by the setup wizard becomes admin everywhere. Roles
attach to the user, not to a tenant. There is no way to say "admin of this
tenant" or "member of that tenant". There is also no role for platform-level
actors. The only admin role mixes "owns this tenant" with "owns the whole
system". That mix blocks shared tenants later. It also reads wrong today.
The wizard user is really two things at once, a tenant admin and the
instance owner.

## Solution

Split role grants into two kinds. Tenant roles bind a user to one tenant
and say what the user may do inside it. System roles bind a user to the
platform itself and are independent of any tenant. The setup wizard grants
the first user admin and member in the personal tenant it creates, plus the
new system_owner role. The API reports tenant roles and system roles
separately, so apps can tell the two kinds apart.

## User Stories

1. As an instance owner, I want the setup wizard to grant me admin in my
   own tenant, so that I can manage the instance I created.
2. As an instance owner, I want the setup wizard to grant me the
   system_owner role, so that my platform power is separate from my tenant
   power.
3. As an instance owner, I want my roles bound to my tenant, so that my
   rights cannot leak into another tenant.
4. As a tenant admin, I want members I create to hold member in their own
   tenant, so that default access stays small.
5. As a tenant admin, I want the users list gated on tenant admin, so that
   members cannot manage users.
6. As a tenant member, I want my roles recognized only in my tenant, so
   that no other tenant can treat me as staff.
7. As a signed-in user, I want `/me` to return my tenant roles, so that
   apps can render what I may do in the current tenant.
8. As a signed-in user, I want `/me` to return my system roles separately,
   so that tenant power and platform power stay distinguishable.
9. As a platform operator, I want a system role no tenant can grant or
   revoke, so that platform duties are not faked with a tenant admin role.
10. As a future system user, I want a system role that works without
    touching any tenant, so that machine upkeep never needs tenant staff.
11. As a security reviewer, I want admin checks to compare the role tenant
    with the session tenant, so that cross-tenant privilege is impossible.
12. As a developer, I want tenant-role writes checked against the ambient
    tenant scope, so that a role row can never point at a foreign tenant.
13. As a developer, I want the role CHECK constraints derived from the role
    enums, so that database and code cannot drift.
14. As a developer, I want a migration that carries every existing grant
    into the new tables, so that upgrading loses nothing.
15. As a maintainer, I want the earliest user to become system_owner in the
    migration, so that every existing instance keeps a platform owner.
16. As a maintainer, I want the old grant table dropped only after nothing
    reads it, so that every deploy step stays shippable and reversible.
17. As a web user, I want my account page to show tenant roles and system
    roles apart, so that I understand my own powers.
18. As a system owner, I want a system section in the sidebar, so that
    platform-level places are separate from tenant places.
19. As a system owner, I want a settings link with an icon in that
    section, so that I can reach instance-level controls.
20. As a member, I want the system section hidden from my sidebar, so that
    the navigation never teases places I cannot use.
21. As an instance owner, I want setup to keep the one-cookie flow, so
    that nothing changes about how I first sign in.

## Implementation Decisions

- The single grant table is replaced by two extension tables. Core users
  stay minimal, per the extensible-entity rule.
- The tenant-roles table holds a user id, a tenant id, and a role. The
  tenant id is NOT NULL and references tenants. The role is limited by a
  CHECK to admin and member. A unique rule covers user, tenant, and role.
  User rows cascade on delete, and the user id is indexed.
- The system-roles table holds a user id and a role. The role is limited by
  a CHECK to system_owner. A unique rule covers user and role. It has no
  tenant column, so the tenant flush guard keeps skipping it, exactly as it
  skips the current grant table.
- Code carries two enums. The tenant Role enum keeps admin and member. A
  new SystemRole enum starts with system_owner. The CHECK SQL is derived
  from the enums, as it is today.
- Because tenant roles carry a tenant id, the tenant flush guard now checks
  their writes. Registration already runs inside the tenant scope it
  creates. Bootstrap grants its roles after that scope ends, so bootstrap
  must grant them inside a tenant scope.
- Bootstrap creates the personal tenant and link as today, then grants
  member and admin in that tenant, then grants system_owner.
- Admin-created users keep today's grant: member in their own personal
  tenant.
- Admin gating checks the tenant admin role. The role's tenant must equal
  the principal's session tenant. After the backfill every grant points at
  the user's linked tenant, so the rule holds by construction. It is stated
  now so shared tenants cannot break it later.
- The principal gains a system-roles tuple. `/me` keeps its roles list as
  the tenant roles of the session tenant. It adds an additive system roles
  list. The session payload is unchanged: one tenant id per session, taken
  from the personal tenant.
- The user-tenant link stays one-to-one. Its uniqueness stays. Multi-tenant
  membership stays out of scope.
- The migration is expand and contract. Expand adds both tables. The
  backfill turns each old grant into a tenant role in the user's linked
  tenant. The earliest user becomes system_owner, matching the old admin
  backfill rule. Contract drops the old grant table and its CHECK once no
  code reads it.
- The web client type gains a system roles field, and the fixtures pinning
  the response shape update. The account page renders the system roles
  list apart from the tenant roles. The sidebar grows a system section,
  visible only to system owners, holding a settings link with a gear
  icon. The settings page is an owner-only placeholder; direct visits by
  non-owners redirect to the dashboard. The wizard copy stays valid.

## Testing Decisions

- Tests check external behavior only: HTTP responses, database state after
  setup, and database state after migration. No internal helpers.
- HTTP seam. After setup, the created user holds admin and member in the
  created tenant and system_owner in the system table. `/me` returns the
  roles and system roles lists with the right shapes. The users router
  returns 403 for members and 200 for admins. Prior art: the setup tests,
  the roles tests, and the gated users tests.
- Migration seam. Upgrading a scratch database through all revisions
  creates both tables with the exact DDL. The backfill moves every old
  grant into the user's tenant. The earliest user gains system_owner. The
  final revision drops the old table. Prior art: the migration tests and
  the role migration tests.
- Guard. A tenant-role write outside any scope fails, and the same write
  inside the right scope passes. Prior art: the tenant scope tests.
- Web. Vitest covers the `/me` parsing with the system roles list present,
  updates the fixtures that pin the response shape, and pins the sidebar
  section rule: the system section appears only for system owners. Prior
  art: the upstream and session tests.
- Every test must be able to fail. Run the falsegreen structural pass and
  the test-smell review on new and touched tests.

## Out of Scope

- Multiple tenants per user, and lifting the one-to-one user-tenant link.
- Tenant switching, or tenant id in the session payload changing meaning.
- Provisioning additional system users, or system users without a tenant.
- Endpoints or UI to grant or revoke roles.
- Any new role value beyond system_owner, admin, and member.
- Changes to the login flow or the session cookie.

## Further Notes

- The companion visual is `spec.html` beside this file. It shows the target
  shape, the before and after role model, and the test seam.
- This spec supersedes the setup-wizard spec note that said the grant table
  carries no tenant id so the guard skips it. Tenant roles now carry one on
  purpose, and the guard checks them.
- The decision record on the tenant link stays intact. The one-to-one link
  stays, and the rejected many-to-many membership stays rejected until a
  tenant selection rule exists. The session tenant would become that rule
  in a later spec.
- The planned registration spec defers org tenants and extra roles. This
  spec builds the base that work will need.
