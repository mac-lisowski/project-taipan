# Rootless uid mapping breaks bind-mount writes

Host uid 1000 = container uid 0. Bind mounts look root-owned inside.
Non-root container users cannot write them. Devcontainers on this
host must run as root.
