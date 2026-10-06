# Infisical first boot is slow; keep Postgres same-region

Fresh instance runs ~770 table migrations plus post-boot fixups. On a
cross-region Railway Postgres (service in asia-southeast1, DB in US)
it crawled 20+ min; same-region finished in ~90s. Check DB region
before assuming the deploy is stuck. KMS surface verified live on
v0.165.16: create KMS project via POST /api/v2/workspace type:kms,
keys under /api/v1/kms/keys, encrypt/decrypt bodies are base64,
DELETE /api/v1/workspace/{id} tears down project + keys.
