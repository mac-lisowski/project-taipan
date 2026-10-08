"""Provisioning find ops and hardened key create.

Unit tests drive a fake transport, so they never skip. Live tests
carry the live_only guard per suite convention; the duplicate-name
test owns both of its projects and deletes them in a finally, the
shared fixture only cleans its own project.
"""

import uuid

import pytest
from kms import KmsError
from kms.infisical_provisioner import InfisicalProvisioner
from kms_testsupport import INFISICAL_URL, TOKEN, live_only


class FakeTransport:
    """Records requests, replays scripted outcomes in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.outcomes: list[dict | Exception] = []

    def request(self, method: str, path: str, json: dict | None = None) -> dict:
        self.calls.append((method, path, json))
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return {}


def make_provisioner(fake: FakeTransport) -> InfisicalProvisioner:
    provisioner = InfisicalProvisioner("http://127.0.0.1:1", "unused-token")
    provisioner._transport = fake
    return provisioner


def test_create_key_body_pins_hardened_defaults() -> None:
    fake = FakeTransport()
    fake.outcomes = [{"key": {"id": "key-1"}}]
    provisioner = make_provisioner(fake)
    assert provisioner.create_key("proj-1", "platform-key") == "key-1"
    assert fake.calls == [
        (
            "POST",
            "/api/v1/kms/keys",
            {
                "projectId": "proj-1",
                "name": "platform-key",
                "algorithm": "aes-256-gcm",
                "keyUsage": "encrypt-decrypt",
                "isExportable": False,
                "hasDeleteProtection": True,
            },
        )
    ]


def test_find_project_filters_kms_list_by_exact_name() -> None:
    fake = FakeTransport()
    # Decoy contains the target, so a substring matcher fails this test.
    fake.outcomes = [{"projects": [{"id": "p1", "name": "mines"}, {"id": "p2", "name": "mine"}]}]
    assert make_provisioner(fake).find_project("mine") == "p2"
    assert fake.calls[0][:2] == ("GET", "/api/v1/projects?type=kms")


def test_find_project_returns_none_when_absent() -> None:
    fake = FakeTransport()
    fake.outcomes = [{"projects": [{"id": "p1", "name": "other"}]}]
    assert make_provisioner(fake).find_project("missing") is None


def test_find_project_raises_loud_on_duplicate_names() -> None:
    fake = FakeTransport()
    fake.outcomes = [{"projects": [{"id": "p1", "name": "dupe"}, {"id": "p2", "name": "dupe"}]}]
    with pytest.raises(KmsError, match="dupe"):
        make_provisioner(fake).find_project("dupe")


def test_find_key_maps_404_to_none() -> None:
    fake = FakeTransport()
    fake.outcomes = [
        KmsError("GET /api/v1/kms/keys/key-name/nope?projectId=p1 failed: 404 {}", status_code=404)
    ]
    assert make_provisioner(fake).find_key("p1", "nope") is None


def test_find_key_returns_wrapped_id() -> None:
    fake = FakeTransport()
    fake.outcomes = [{"key": {"id": "k9"}}]
    assert make_provisioner(fake).find_key("p1", "mine") == "k9"
    assert fake.calls[0][:2] == ("GET", "/api/v1/kms/keys/key-name/mine?projectId=p1")


def test_find_key_reraises_non_404_errors() -> None:
    fake = FakeTransport()
    fake.outcomes = [KmsError("GET /api/v1/kms/keys failed: 500 boom", status_code=500)]
    with pytest.raises(KmsError):
        make_provisioner(fake).find_key("p1", "mine")


def test_find_key_reraises_transport_level_errors() -> None:
    # No HTTP status (connection refused and friends) is not a 404:
    # an implementation mapping None to absent would create duplicates.
    fake = FakeTransport()
    fake.outcomes = [KmsError("GET /api/v1/kms/keys failed: ConnectError")]
    with pytest.raises(KmsError):
        make_provisioner(fake).find_key("p1", "mine")


@live_only
def test_find_project_returns_none_for_unknown_name() -> None:
    provisioner = InfisicalProvisioner(INFISICAL_URL, TOKEN)
    assert provisioner.find_project(f"taipan-test-{uuid.uuid4().hex}") is None


@live_only
def test_find_project_finds_the_fixture_project(keys) -> None:
    assert keys.provisioner.find_project(keys.project_name) == keys.project_id


@live_only
def test_find_project_raises_when_two_projects_share_a_name(keys) -> None:
    name = f"taipan-test-{uuid.uuid4().hex}"
    first = keys.provisioner.create_project(name)
    second = keys.provisioner.create_project(name)
    try:
        with pytest.raises(KmsError, match=name):
            keys.provisioner.find_project(name)
    finally:
        keys.provisioner.delete_project(first)
        keys.provisioner.delete_project(second)


@live_only
def test_find_key_returns_none_before_and_id_after_create(keys) -> None:
    # Key names cap at 32 chars, so the uuid rides truncated.
    name = f"taipan-test-key-{uuid.uuid4().hex[:12]}"
    assert keys.provisioner.find_key(keys.project_id, name) is None
    key_id = keys.provisioner.create_key(keys.project_id, name)
    # No key teardown: the fixture deletes the whole throwaway project.
    assert keys.provisioner.find_key(keys.project_id, name) == key_id


@live_only
def test_create_key_roundtrips_with_the_same_adapter(keys) -> None:
    name = f"taipan-test-key-{uuid.uuid4().hex[:12]}"
    key_id = keys.provisioner.create_key(keys.project_id, name)
    plaintext = b"taipan create-key secret"
    ciphertext = keys.provisioner.encrypt(key_id, plaintext)
    assert keys.provisioner.decrypt(key_id, ciphertext) == plaintext
