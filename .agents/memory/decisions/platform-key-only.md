# One platform KMS key, no per-tenant keys

Field encryption wraps every per-tenant DEK with one platform-wide
Infisical KMS key (`API_INFISICAL_KMS_KEY_ID`). Per-tenant
wrapping keys were evaluated 2026-10-08 and dropped, not
deferred.

Why: tenant isolation already exists at the DEK level (each
tenant has its own data key; AAD binds tenant_id and key_id into
every ciphertext). Per-tenant crypto-shredding already works:
account delete removes the tenant_deks row. A tenant is a
personal tenant per user today, so per-tenant keys would mean
one KMS key per signup. Provisioning keys at registration would
also put the admin identity into the runtime request path,
breaking the two-identity rule in packages/kms.

Rejected: per-tenant KMS keys. They cost one KMS key per signup.
Their benefit, independent rotation and BYOK, only matters for org
tenants. No org tenants exist yet. KeyResolver, tenant_deks.key_id,
and the envelope key id stay in place, so a reversal stays cheap.

Cost accepted: wrap-key rotation and compromise blast radius are
platform-wide, not per tenant.
