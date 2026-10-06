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

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

## Scopes

App and package scopes come from the repo itself (`apps/*`,
`packages/*`) and the hook picks them up on its own:

`api`, `web`, `cli`, `core`, `crypto`, `kms`.

Generic scopes for repo-wide areas:

`repo`, `ci`, `docs`, `deps`, `scripts`, `evals`, `docker`,
`devcontainer`, `agents`, `hooks`, `github`.

Update rule: adding a top-level area adds its generic scope here
and in `scripts/check-commit-msg.sh`. No gate change is needed
for a new app or package.

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
