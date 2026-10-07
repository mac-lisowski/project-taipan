# Build context is the repo root (scripts/check-docker.sh asserts
# root-relative COPY sources):
#   docker build -f docker/nats/Dockerfile -t taipan-nats .
# Default CMD is the compose conf (MQTT on, see docker-compose.yaml).
# The Railway service overrides the start command for its profile:
#   nats-server -c /etc/nats/nats-railway.conf
# The pinned tag is the single source for the broker version in every
# env. See docs/messaging.md for the Railway setup.
FROM nats:2.15-alpine

COPY docker/nats/nats.conf docker/nats/nats-railway.conf /etc/nats/

CMD ["nats-server", "-c", "/etc/nats/nats.conf"]
