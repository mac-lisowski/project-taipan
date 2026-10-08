# System settings are global and owner guarded

- One global key value table holds platform settings; no tenant_id.
- First key: registration_enabled, default false (sign up starts closed).
- Guard is require_system_owner, never require_admin.
- Why: admin is tenant-scoped (roles filtered to the session tenant);
  a tenant admin holding a global switch leaks platform control
  across tenants.
- Shipped web settings page already gates on system owner only.
- When the switch is off: API sign up endpoint 404, web register
  route 404, no sign up links render anywhere (login page included).
- Public switch read through the BFF exposes the switch and nothing
  else; it feeds route gating and link rendering.
- Spec: docs/specs/implemented/registration/spec.md (2026-10-08).
