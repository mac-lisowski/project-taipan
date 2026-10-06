# testcontainers use a sibling dind service

Privileged `dind` service with `DOCKER_HOST=tcp://dind:2375` instead
of the host socket. Keeps test containers off the host daemon and
avoids rootless socket quirks.
