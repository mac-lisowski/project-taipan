# Docker build context is the repo root

Every apps/*/Dockerfile builds with repo-root context (api set the
convention; web follows). scripts/check-docker.sh enforces that each
COPY source resolves root-relative; CI builds each image via
`scripts/docker-build.sh <app>` which wraps
`docker build -f apps/<app>/Dockerfile -t taipan-<app> .`. A single
root `.dockerignore` covers all builds; apps keep no own file.
