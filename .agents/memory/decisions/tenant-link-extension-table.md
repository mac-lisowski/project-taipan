# Tenant link lives in user_tenants, not on users

The user-to-tenant link is a `user_tenants` extension table row
(`user_id` unique FK cascade, `tenant_id` NOT NULL FK), not a
`tenant_id` column on `users`. Pattern A's closed identity list
(id, email, hashed_password, is_active, timestamps - "nothing
else") stays closed.

Why: `EncryptedString` reads the ambient `tenant_scope`
ContextVar, never a row attribute, so the crypto layer is
agnostic to where the link lives. The middleware resolves it in
the same single query either way (join instead of column).
Rejected: `users.tenant_id` (violates the closed list, buys
nothing at runtime), `tenant_memberships` N:M (no selection rule
means silent mis-scoping), `tenants.owner_id` (breaks ADR-0001's
generic "tenant can be user or organization").

Cost accepted: "no tenantless user" is helper- and test-enforced,
not NOT NULL enforced. A missing link row fails closed: the
request runs unscoped and encrypted writes raise.
