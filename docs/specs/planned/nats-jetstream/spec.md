# Spec: NATS JetStream messaging on Railway

Status: planned.

Seam: one messaging seam owns publish, subscribe, and queue shapes over an injected NATS link. The API config seam owns the broker URL. Routers and workers stay thin.

## Problem Statement

There is no shared async path. Background jobs, service events, and device messages each need a home. Kafka and RabbitMQ are too heavy to run and to keep up. Local, devcontainer, and Railway must share one light shape.

## Solution

One NATS server with JetStream serves all three needs. Jobs use durable work queues with ack and retry. Events use core subjects for fast signals and streams for replay. Devices use the built-in MQTT port. The same broker image runs local, in the devcontainer, and on Railway. The app reads one URL from env and still boots when the broker is down.

## User Stories

1. As a dev, I want one broker for jobs plus events plus device mail, so that I run less infra.
2. As a dev, I want the broker up with one compose command, so that local start stays fast.
3. As a dev, I want the same broker inside the devcontainer, so that host and container agree.
4. As an operator, I want NATS as its own Railway service from a pinned image, so that deploys stay repeatable.
5. As an operator, I want the API to get the broker URL from env, so that no host name is baked in.
6. As an operator, I want JetStream data on a named volume, so that streams survive restarts.
7. As an API dev, I want one messaging seam for publish and subscribe, so that routers stay thin.
8. As a worker dev, I want queue groups with ack, so that each job runs once per pool.
9. As a worker dev, I want retry with a dead letter subject, so that bad jobs do not block the queue.
10. As a service dev, I want fast core subjects for signals, so that hot paths stay quick.
11. As a service dev, I want durable streams for key events, so that late readers can replay.
12. As a service dev, I want one stream per domain, so that retention rules stay clear.
13. As a device dev, I want MQTT on the broker, so that small devices use plain MQTT.
14. As a device dev, I want edge bridging as an option, so that weak links still deliver.
15. As an API dev, I want boot with the broker down, so that a broker outage does not kill the API.
16. As an operator, I want health to report broker state, so that checks see the truth.
17. As an operator, I want client, monitor, and MQTT ports split, so that only needed ports open per env.
18. As a tester, I want a fake of the messaging seam, so that unit tests run with no broker.
19. As a tester, I want contract tests with a real broker, so that shapes match the server.
20. As a newcomer, I want one doc for URL vars and subject names, so that first use is clear.
21. As an operator, I want memory-only mode for tests, so that test runs leave no state.
22. As a maintainer, I want no Kafka protocol compat, so that scope stays small.

## Implementation Decisions

- One broker serves all traffic. NATS with JetStream is the single binary and image in every env. No second broker is added.
- JetStream is on in every env. File store backs local, devcontainer, and Railway volumes. Memory store is test only.
- Streams map to domains. One stream per domain owns its subjects plus retention. Consumers map to worker pools.
- Core subjects carry fast signals with no persist. Streams carry events that need replay and jobs that need ack.
- Workers use queue groups with explicit ack. Retry uses redelivery with a cap. Overflow goes to a dead letter subject per domain.
- MQTT is on at the broker for devices. Devices speak plain MQTT while services speak NATS on the same subjects.
- Edge bridging is optional. A tiny edge broker may bridge to the central broker. It is off unless a site needs it.
- The API config seam owns one URL var with a localhost default. Each stack points it at its own broker host. Hosts are never baked in.
- Connect is lazy and the app boots brokerless. Readiness and health report broker state but boot never waits on it.
- All NATS code lives in one reusable messaging package. Apps only wire routes, workers, and stream names. Packages never import from apps.
- The Railway broker is its own service from a pinned NATS image with a mounted volume. The API service only holds the URL var. No broker code ships in the API image.
- Ports stay split by role. The client port serves services, the monitor port serves checks, and the MQTT port serves devices. Each env opens only what it needs.
- Subject names and stream names follow one naming doc. Names carry domain plus kind plus version. Payloads stay small JSON.

## Testing Decisions

- A good test pins outside behavior only. It sends through the seam and reads the effect. It never asserts client internals.
- Config tests pin the URL default, env override, and bad value errors. They use plain maps and need no broker.
- Seam tests use a fake adapter. They assert one publish per action, queue shape per worker pool, and retry to dead letter.
- Contract tests use a real broker. They cover publish then receive, worker ack, redelivery on nack, replay from a stream, and MQTT publish to NATS subject.
- Boot tests pin brokerless start. They stop the broker and assert the API still boots and health reports the broker as down.
- Compose tests validate both stacks. They parse the stack files and assert the broker service, the volume mount, and the URL var agree.
- Prior art is the API HTTP suite with a real test database and the shared email seam with a fake adapter. Messaging tests copy that split.

## Out of Scope

- Real job types and event schemas.
- Device fleet care and firmware.
- Full auth story beyond basic broker creds.
- Multi node clustering and geo replication.
- Dashboards and alert rules.
- Move from Kafka or RabbitMQ.
- Billing and usage caps on Railway.

## Further Notes

- The visual lives beside this file in spec.html. It shows the module seam, the depth shift, and the test seam.
- Pact holds. One messaging seam serves jobs, events, and device mail. Config owns the broker URL. Railway runs the broker as its own service with a volume.
