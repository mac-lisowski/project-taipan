# setup-node cache: pnpm needs pnpm to exist first

GitHub Actions: `setup-node` with `cache: pnpm` runs pnpm during its
own step to resolve cache paths, so pnpm must already exist.
`corepack enable` in a later step is too late. Use
`pnpm/action-setup` BEFORE `setup-node`, and set its
`package_json_file: apps/web/package.json` - it defaults to the
repo-root package.json which does not exist here.
