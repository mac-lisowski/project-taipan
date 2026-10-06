# Commit convention

All commit messages follow Conventional Commits 1.0.0
([spec](https://www.conventionalcommits.org/en/v1.0.0/)).

## Format

```
<type>(optional scope)(optional !): <description>
```

- `type` is required, lowercase, one of the list below.
- `scope` is optional. When present it must be in the allowed list.
  Scope chars are lowercase letters, digits, and hyphens.
- `!` marks a breaking change, e.g. `feat(api)!: drop v1`.
- One space follows the colon. Description is imperative, no trailing period.
- Subject and every body line stay within 120 chars.
- `Merge ...`, `Revert ...`, `fixup!`, `squash!`, `amend!` subjects
  skip the format check.

## Types

<!-- conventions:types:start -->
`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.
<!-- conventions:types:end -->

## Scopes

App and package scopes come from the repo itself (`apps/*`,
`packages/*`) and the hook picks them up on its own:

<!-- conventions:areas:start -->
`api`, `cli`, `core`, `crypto`, `kms`, `web`.
<!-- conventions:areas:end -->

Generic scopes for repo-wide areas:

<!-- conventions:generic:start -->
`repo`, `ci`, `docs`, `deps`, `scripts`, `evals`, `docker`,
`devcontainer`, `agents`, `hooks`, `github`.
<!-- conventions:generic:end -->

Update rule: edit `scripts/conventions.sh`, then run
`scripts/sync-conventions-docs.sh` and commit both. The lists
above are generated. No gate change is needed for a new app
or package.

## Branches

Branch names use the same types: `<type>/<slug>`, e.g. `feat/web-bff`.
Slug chars are lowercase letters, digits, and hyphens.
`main`, `dev`, `master`, and detached HEAD are exempt.

## Examples

```
feat(api): add tenant filter to user list
fix(web): keep focus on login error
docs: rewrite README quickstart
chore(deps): bump ruff to 0.16.10
feat(crypto)!: change default cipher suite
```

## Agent tip

Read this file before committing. If the hook rejects a scope,
the scope is either misspelled or missing from the list above.
