# Learnings index

Durable lessons, gotchas, user preferences. One topic per file in
`learnings/`; when you add a file, add its link here.

## User preferences

- [User preferences](learnings/user-preferences.md)

## Gotchas

- [Docker daemon is rootless](learnings/docker-rootless.md)
- [Postgres+pgvector via compose; tests need it](learnings/postgres-compose.md)
- [httpx2 imports as httpx](learnings/httpx2-import.md)
- [Rootless uid mapping breaks bind-mount writes](learnings/rootless-uid.md)
- [pre-commit install bakes INSTALL_PYTHON](learnings/pre-commit-install-python.md)
- [uv workspace glob matches apps/web](learnings/uv-workspace-glob.md)
- [setup-node cache needs pnpm first](learnings/gha-pnpm-order.md)
- [next typegen before tsc on clean checkout](learnings/next-typegen.md)
- [Verify CI jobs locally with act](learnings/act-local-ci.md)
- [Guard gateway JSON before iterating](learnings/gateway-json-payload-guard.md)
- [docker build apps/web tested a different context](learnings/docker-context-mismatch.md)
- [corepack resolves packageManager from cwd, not -C](learnings/corepack-pnpm-cwd.md)
- [Rootless containers cannot reach host-bound services](learnings/rootless-no-host-access.md)
- [nextUrl.origin is client-controlled](learnings/nexturl-origin-untrusted.md)
- [Module-level env throws break next build](learnings/next-build-env-eval.md)
- [CI smoke tests bind ephemeral ports](learnings/ci-ephemeral-ports.md)
- [.dockerignore patterns are root-anchored](learnings/dockerignore-anchored.md)
- [Railway deploys run from CI, not the GitHub app](learnings/railway-github-deployments.md)
- [Job skipped because an upstream needs job was skipped](learnings/gha-skip-propagates.md)
- [npx skills CLI behavior in this repo](learnings/skills-cli.md)
- [Heredoc payloads tripped pre-exec gates](learnings/hook-heredoc-false-positive.md)
- [falsegreen vs falsegreen-js output formats differ](learnings/falsegreen-js-format.md)
- [Hook root resolution: script location before cwd](learnings/hook-root-resolution.md)
- [Editing live hook files is a loaded gun](learnings/hook-editing-lockout.md)
- [Diff hash binds worktree content, not diff position](learnings/diff-hash-staging-invariance.md)
- [Canonicalize paths via pwd -P, never string surgery](learnings/path-normalization-squeeze.md)
- [Infisical SITE_URL needs https:// or it 502s](learnings/infisical-site-url.md)
- [Infisical first boot slow; keep Postgres same-region](learnings/infisical-first-boot.md)
- [Rewrite current.md, never append history](learnings/memory-hygiene.md)
- [httpx2 retries requests that lose their response](learnings/httpx2-retry-lost-response.md)
- [`bl` on PATH is Blaxel, not Bailian](learnings/bl-binary-collision.md)
- [gh --env 404s on spaces+slash env names](learnings/gh-env-name-encoding.md) - use raw API with %20%2F%20 + pynacl sealed box
- [Explicit pytest args break conftest imports](learnings/pytest-arg-conftest-collision.md)
- [OpenUI composer unmounts on Route views; slots.rest stays mounted](learnings/openui-composer-route-slots.md)
- [git-grep gates need git add -N on new files](learnings/git-grep-gates-need-add-n.md)
- [OpenUI SDK pane hooks](learnings/openui-sdk-pane-hooks.md)
- [Review stamp binds to the session checkout, not a worktree](learnings/worktree-commit-stamp.md)
- [Request commit happens in the get_db teardown](learnings/commit-boundary-teardown.md)
- [BFF proxy strips Content-Length both directions](learnings/bff-strips-content-length.md)
- [BFF proxy aborts upstream calls at 30 s](learnings/bff-upstream-timeout.md)
