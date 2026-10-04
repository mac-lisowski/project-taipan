# Decisions

- Prefer domain-named packages where they fit. Design packages to be
  shareable and reusable, not app-specific.
- Dev dep is `httpx2` (httpx fork), not `httpx`. starlette TestClient
  supports it natively.
