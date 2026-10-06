# Conventional commit gate

- Hook checks `<type>(scope)!: description`; scope optional.
- App and package scopes derive from `apps/*`, `packages/*` at hook run time.
- Generic scopes live in `docs/commit-convention.md` and the hook script; keep both in sync.
- CI lints PR titles on pull requests, commit ranges on push.
- Merge, Revert, fixup!, squash!, amend! subjects skip format check; length gate still runs.
- Old history is not conformant; gate covers new commits only.
