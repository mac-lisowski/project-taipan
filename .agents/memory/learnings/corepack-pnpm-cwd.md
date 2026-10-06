# corepack resolves packageManager from cwd, not -C

Inside a Dockerfile, `pnpm -C <dir>` does NOT make corepack pick up
`<dir>/package.json` packageManager: version resolution happens on
the process cwd first and `ERR_PNPM_BAD_PM_VERSION` hits when they
differ. Use `WORKDIR <dir>` or `cd <dir> && pnpm`.
check-docker.sh flags `pnpm -C/--dir` in RUN lines now.
