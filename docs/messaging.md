# Messaging: NATS JetStream

One NATS broker with JetStream serves jobs, events, and device mail.
The same pinned image (`nats:2.15-alpine`) runs local, in the
devcontainer, and on Railway. The conf files live in `docker/nats/`.
The package code lives in `packages/messaging/`. The code is the
source for every shape below. This doc only names the rules and
points at the code.

## URL vars

| Var | Meaning | Default |
| --- | ------- | ------- |
| `API_BROKER_URL` | Client URL the API dials. The app boots with the broker down. | `nats://localhost:4222` |
| `API_JETSTREAM_STORE` | JetStream storage for new streams: `file` or `memory`. | `file` |

The config seam `apps/api/src/api/config.py` owns both vars. A blank
`API_BROKER_URL` fails at load. So does a store value outside
`file` and `memory`.

Host per environment:

| Environment | `API_BROKER_URL` | Set where |
| ----------- | ---------------- | --------- |
| Host, root compose | `nats://localhost:4222` | code default, no setup |
| Devcontainer | `nats://nats:4222` | `.devcontainer/docker-compose.yml` |
| Railway | URL of the broker service | env var on the API service |

No host name is baked into code or images. Each stack points the var
at its own broker. On Railway only the API service holds the URL.
The API image carries no broker code.

## Subjects and streams

The subject grammar is `<domain>.<kind>.<version>`, for example
`mail.sent.v1`. The helper `subject()` in
`packages/messaging/src/messaging/seam.py` is the single source.
Publishers and stream declarations share it, so names cannot drift.

Rules as implemented in the package:

- One stream per domain. `define_stream()` declares it and is safe to
  call again. An existing stream stays as is.
- A stream name is the domain with dots folded to dashes. `mail`
  stays `mail`; `a.b` becomes `a-b`.
- Retention lives on the stream, per domain: `limits`, `interest`, or
  `workqueue`. It is never a global setting.
- Plain names are one token of letters, digits, underscore, and dash.
  A subject pattern may also carry whole-token wildcards.

## Queue groups and dead letters

One worker pool is one durable consumer plus one queue group. Every
worker passes the same durable name and the same queue group name to
`subscribe_durable()`. Both names follow the plain token rule above.

- A job runs once per pool.
- `nak()` schedules a redelivery, up to the delivery cap (default 3).
- Past the cap the job moves once to the dead letter subject:
  `<domain>.dlq`, built by `dead_letter_subject()`. A bad job never
  blocks the queue.

## Ports

| Port | Role | Root compose | Devcontainer | Railway |
| ---- | ---- | ------------ | ------------ | ------- |
| 4222 | NATS client | published to host | network only | open |
| 8222 | Monitor, `/healthz` | published to host | network only | open |
| 1883 | MQTT for devices | published to host | network only | off |

- Root compose (`docker-compose.yaml`) publishes all three ports.
  The code default `nats://localhost:4222` works there as is.
- The devcontainer publishes no host ports. The app reaches the
  broker on the compose network as `nats:4222`. MQTT 1883 is reachable
  on that network only.
- Railway opens client 4222 and monitor 8222 only. Devices are not on
  Railway, so `docker/nats/nats-railway.conf` has no MQTT block.

Devices speak plain MQTT on 1883 where that port is open. Their
messages land on NATS subjects, so devices and services share one
topic space.

## Store modes

- `file` is the default and the mode for every real environment. The
  broker writes JetStream data to `/data`. That path is a named
  volume in both compose stacks and on Railway. Streams survive
  restarts.
- `memory` is for tests. Set `API_JETSTREAM_STORE=memory` and a test
  run leaves no state on disk.

Storage is per stream. The adapter maps the configured mode onto each
stream it creates (`packages/messaging/src/messaging/nats_streams.py`).

## Health

`GET /health` on the API reports the broker link as a
`broker.connected` flag. It reads cached link state only. It never
pings the broker and never opens a connection. Boot never waits for
the broker. Source: `apps/api/src/api/routers/health.py`.

## Edge bridging

Edge bridging is optional. A tiny broker at a site may bridge to the
central broker over a weak link. It is off unless a site needs it.

The mechanism is a `leafnodes` block with a `remotes` entry in that
site's `nats.conf`. The repo ships no such config. A site that needs
the bridge adds its own.

## Railway ops

1. Create a service from this repo. Set `dockerfilePath` to
   `docker/nats/Dockerfile`.
2. Set the start command to
   `nats-server -c /etc/nats/nats-railway.conf`.
3. Mount a volume at `/data`. Streams survive restarts there.
4. Open client 4222 and monitor 8222 only.
5. Set `API_BROKER_URL` on the API service only. It points at the
   broker service. The API image carries no broker code.
