# Module-level env throws break next build

`next build` page-data collection evaluates route modules with
NODE_ENV=production but without runtime env. A top-level `throw` on
a missing env var fails the build. Resolve env lazily inside the
handler.
