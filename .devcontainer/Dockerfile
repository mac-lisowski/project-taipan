FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# uv binary, pinned to the version used on the host.
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /usr/local/bin/

# Docker CLI. Talks to the sibling dind daemon via DOCKER_HOST
# (testcontainers in the devcontainer needs a daemon to spawn into).
COPY --from=docker:28-cli /usr/local/bin/docker /usr/local/bin/docker
