"""Compose tests: both stacks pin the same broker shape.

Parses the two stack files only. No docker daemon and no broker. The
pinned values come from the spec: one image everywhere, JetStream file
store on a named volume, ports split by role (client 4222, monitor
8222, MQTT 1883), and each stack points the app at its own broker host.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_STACK = REPO_ROOT / "docker-compose.yaml"
DEVCONTAINER_STACK = REPO_ROOT / ".devcontainer" / "docker-compose.yml"

PINNED_IMAGE = "nats:2.15-alpine"
CLIENT_PORT = 4222
MONITOR_PORT = 8222
MQTT_PORT = 1883


def _stack(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _nats_service(stack: dict) -> dict:
    return stack["services"]["nats"]


def _data_volume_source(service: dict) -> str | None:
    """Source of the /data mount, or None when the service has none."""
    for mount in service.get("volumes", []):
        source, _, target = str(mount).partition(":")
        if target == "/data":
            return source
    return None


def test_both_stacks_define_nats_service_with_pinned_image() -> None:
    for path in (ROOT_STACK, DEVCONTAINER_STACK):
        service = _nats_service(_stack(path))
        assert service["image"] == PINNED_IMAGE
        assert "latest" not in service["image"]


def test_both_stacks_mount_named_volume_at_data() -> None:
    for path in (ROOT_STACK, DEVCONTAINER_STACK):
        stack = _stack(path)
        source = _data_volume_source(_nats_service(stack))
        # Named volume: declared at top level, not a host bind path.
        assert source in stack.get("volumes", {}), path
    assert _data_volume_source(_nats_service(_stack(ROOT_STACK))) == "natsdata"


def test_root_stack_publishes_client_monitor_and_mqtt_ports() -> None:
    service = _nats_service(_stack(ROOT_STACK))
    host_ports = {int(str(p).split(":")[0]) for p in service["ports"]}
    assert host_ports == {CLIENT_PORT, MONITOR_PORT, MQTT_PORT}


def test_devcontainer_nats_publishes_no_host_ports() -> None:
    assert "ports" not in _nats_service(_stack(DEVCONTAINER_STACK))


def test_devcontainer_app_env_points_at_compose_broker() -> None:
    stack = _stack(DEVCONTAINER_STACK)
    env = stack["services"]["app"]["environment"]
    assert env["API_BROKER_URL"] == "nats://nats:4222"


def test_root_stack_nats_healthcheck_probes_monitor_healthz() -> None:
    service = _nats_service(_stack(ROOT_STACK))
    probe = " ".join(service["healthcheck"]["test"])
    assert "/healthz" in probe
    assert str(MONITOR_PORT) in probe


def test_devcontainer_app_waits_for_healthy_nats() -> None:
    stack = _stack(DEVCONTAINER_STACK)
    depends = stack["services"]["app"]["depends_on"]
    assert depends["nats"]["condition"] == "service_healthy"
