# Extensible entities via Pattern A

Core database entities (such as User) remain minimal. They hold only
identity and credential fields. Domain extensions attach via separate
1:1 or 1:N extension tables referencing the core entity id. Do not add
domain-specific columns directly to core entity models.
