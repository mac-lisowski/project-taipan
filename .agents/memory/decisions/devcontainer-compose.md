# Devcontainer is self-contained compose

Compose-based: app + db + dind services. Does not merge root
docker-compose.yaml; its 5432 publish would collide on the host.
