# Decisions index

Why things are the way they are. One decision per file in
`decisions/`; when you add a file, add its link here. Append-only.

- [Domain-named packages](decisions/domain-named-packages.md)
- [httpx2 as the dev HTTP client](decisions/httpx2-fork.md)
- [Devcontainer is self-contained compose](decisions/devcontainer-compose.md)
- [Devcontainer runs as root](decisions/devcontainer-root.md)
- [testcontainers use a sibling dind service](decisions/testcontainers-dind.md)
- [Test DB URLs come from env vars](decisions/test-db-env-vars.md)
- [Agent hooks: .agents/hooks + .claude manifest](decisions/agent-hooks.md)
- [Web is a Next.js BFF](decisions/web-bff.md)
- [FastAPI mounts routers under /api](decisions/api-prefix.md)
- [Quality gates: LOC cap + BFF boundary](decisions/quality-gates.md)
- [Docker build context is the repo root](decisions/docker-root-context.md)
- [Specs live in docs/specs/, not an issue tracker](decisions/specs-as-files.md)
- [Done tickets carry an HTML report](decisions/ticket-reports.md)
- [ADR-0001: seam for encrypted model fields](../docs/adr/ADR-0001-seam-for-encrypted-model-fields.md) - TypeDecorator + deep crypto module, envelope encryption, generic tenant_id
- [Extensible entities via Pattern A](decisions/extensible-entities-pattern-a.md)
- [Tenant link lives in user_tenants, not on users](decisions/tenant-link-extension-table.md)
