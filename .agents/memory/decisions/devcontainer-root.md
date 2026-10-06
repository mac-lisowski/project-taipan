# Devcontainer runs as root

Rootless Docker maps host uid to container 0, so a normal user
cannot write the bind mount.
