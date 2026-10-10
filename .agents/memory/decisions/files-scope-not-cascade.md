# Files: scope column + RESTRICT, never CASCADE

From the object-storage spec (docs/specs/implemented/object-storage/).

- `files` rows carry `scope` (`user` | `tenant`). Private files die
  with the user; tenant files survive the uploader while the tenant
  lives.
- `created_by_user_id` is nullable attribution with
  `ON DELETE RESTRICT`, not CASCADE. A cascade would delete the row
  while leaking the S3 object, and would kill tenant files with the
  uploader.
- `files.tenant_id` carries no FK (matches every tenant table), so
  tenant deletes enforce nothing at the DB; they honor the
  `detach_tenant` contract instead.
- User-delete ordering: consumer rows holding file_id refs, then
  `detach_user` (purge private rows+objects, null tenant uploaders),
  then the user row, then `detach_tenant` per deleted tenant (purges
  every file in it), then the tenant row. users.remove already
  deletes the personal Tenant + DEK today.
- Both detaches wrap mutations in `tenant_scope(<victim tenant>)` so
  the flush guard passes under a foreign ambient scope.
