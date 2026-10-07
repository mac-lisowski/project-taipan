"""Live contract: NatsBroker and MQTT gateway against a real broker.

Skip when the broker is unreachable, same convention as the redis live
tests. What only a live run proves: real bytes survive the wire, a
standard consumer replays what the seam published, per-stream storage
matches the configured mode, and an MQTT device publish lands on the
NATS subject. Stream and subject names are unique per run and torn
down, so runs leave no server state behind.
"""

import asyncio
import json
import os
import uuid
from typing import Any
from urllib.parse import urlsplit

import pytest
from messaging import MessagingError
from nats.js.api import StorageType
from nats.js.errors import NotFoundError as JsNotFoundError

MQTT_URL = os.environ.get("TEST_MQTT_URL", "mqtt://localhost:1883")
WAIT = 5.0


@pytest.mark.anyio
async def test_publish_reaches_a_core_subject_subscriber(
    inspector: Any, broker_factory: Any
) -> None:
    broker = broker_factory("memory")
    subject = inspector.subject()
    got: list = []
    arrived = asyncio.Event()

    async def capture(msg) -> None:
        got.append(msg)
        arrived.set()

    await broker.subscribe(subject, capture)
    await broker.publish(subject, {"order_id": 7, "total_cents": 1999})
    assert broker.connected is True

    await asyncio.wait_for(arrived.wait(), timeout=WAIT)
    await broker.drain()

    [msg] = got
    assert dict(msg.payload) == {"order_id": 7, "total_cents": 1999}
    assert msg.subject == subject


@pytest.mark.anyio
async def test_stream_publish_replays_to_a_later_reader(
    inspector: Any, broker_factory: Any
) -> None:
    broker = broker_factory("file")
    stream = inspector.stream()
    subject = inspector.subject()
    await broker.ensure_stream(stream, [subject])
    await broker.publish(subject, {"event": "paid", "n": 1})

    # The consumer starts after the publish: only a stored stream can serve it.
    sub = await inspector.js.pull_subscribe(subject, stream=stream)
    msgs = await sub.fetch(1, timeout=WAIT)
    await broker.drain()

    assert json.loads(msgs[0].data) == {"event": "paid", "n": 1}
    assert msgs[0].subject == subject


@pytest.mark.anyio
async def test_memory_stream_stays_ram_only_on_a_file_store_server(
    inspector: Any, broker_factory: Any
) -> None:
    # Storage is per stream: a memory stream never touches the server
    # store dir, so a test run leaves no disk state behind.
    broker = broker_factory("memory")
    stream = inspector.stream()
    await broker.ensure_stream(stream, [inspector.subject()])
    info = await inspector.js.stream_info(stream)
    await broker.drain()

    assert info.config.storage == StorageType.MEMORY


@pytest.mark.anyio
async def test_file_stream_reports_file_storage(inspector: Any, broker_factory: Any) -> None:
    broker = broker_factory("file")
    stream = inspector.stream()
    await broker.ensure_stream(stream, [inspector.subject()])
    info = await inspector.js.stream_info(stream)
    await broker.drain()

    assert info.config.storage == StorageType.FILE


@pytest.mark.anyio
async def test_drop_stream_removes_the_replay_state(inspector: Any, broker_factory: Any) -> None:
    broker = broker_factory("file")
    stream = inspector.stream()
    await broker.ensure_stream(stream, [inspector.subject()])

    await broker.drop_stream(stream)

    with pytest.raises(JsNotFoundError):
        await inspector.js.stream_info(stream)
    await broker.drain()


@pytest.mark.anyio
async def test_use_after_drain_raises_and_the_link_stays_down(
    inspector: Any, broker_factory: Any
) -> None:
    broker = broker_factory("file")
    subject = inspector.subject()
    await broker.publish(subject, {"ok": True})
    assert broker.connected is True

    await broker.drain()

    with pytest.raises(MessagingError):
        await broker.publish(subject, {"ok": True})
    assert broker.connected is False


@pytest.mark.anyio
async def test_mqtt_publish_lands_on_the_nats_subject(
    inspector: Any, broker_factory: Any, reachable: Any
) -> None:
    # One flat topic name keeps the MQTT/NATS separator mapping out of
    # the test: identity for names with neither / nor . The MQTT client
    # lives in the package dev group, so a run without it skips here.
    mqtt = pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed")
    if not reachable(MQTT_URL):
        pytest.skip("mqtt port not reachable")

    broker = broker_factory("memory")
    topic = f"taipan-live-mqtt-{uuid.uuid4().hex[:12]}"
    got: list = []
    arrived = asyncio.Event()

    async def capture(msg) -> None:
        got.append(msg)
        arrived.set()

    await broker.subscribe(topic, capture)

    device = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"taipan-live-mqtt-{uuid.uuid4().hex[:8]}",
        protocol=mqtt.MQTTv311,
    )
    host = urlsplit(MQTT_URL).hostname or "localhost"
    port = urlsplit(MQTT_URL).port or 1883
    device.connect(host, port, keepalive=30)
    device.loop_start()
    try:
        device.publish(topic, json.dumps({"device": "edge-1", "celsius": 21}).encode(), qos=0)
        await asyncio.wait_for(arrived.wait(), timeout=WAIT)
    finally:
        device.loop_stop()
        device.disconnect()
    await broker.drain()

    [msg] = got
    assert dict(msg.payload) == {"device": "edge-1", "celsius": 21}
