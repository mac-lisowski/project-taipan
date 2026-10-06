# .dockerignore patterns are root-anchored

`.env` only excludes a root-level file. Nested secrets need
`**/.env` - the api image COPYed apps/api/.env into the image until
this was fixed.
