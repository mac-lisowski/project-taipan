# Rootless containers cannot reach host-bound services

host.docker.internal (host-gateway -> 172.17.0.1) and 10.0.2.2 both
fail when the service listens on host loopback. For e2e tests, run
standalone server.js on the host instead.
