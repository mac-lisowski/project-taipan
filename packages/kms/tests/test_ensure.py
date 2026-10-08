"""Create-or-get ensure functions over the Provisioning port.

Unit tests drive a fake Provisioning that records calls and serves
configurable find results, so the idempotence choice is pinned with no
network. The ambiguity case rides the real adapter over a fake
transport, mirroring test_infisical_provisioning.py.
"""

import pytest
from kms import KmsError
from kms.ensure import ensure_key, ensure_project


class FakeProvisioning:
    """Dict-backed finders; create records and starts serving finds."""

    def __init__(
        self,
        project_ids: dict[str, str] | None = None,
        key_ids: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.project_ids = project_ids or {}
        self.key_ids = key_ids or {}
        self.find_project_calls: list[str] = []
        self.find_key_calls: list[tuple[str, str]] = []
        self.created_projects: list[str] = []
        self.created_keys: list[tuple[str, str]] = []

    def find_project(self, name: str) -> str | None:
        self.find_project_calls.append(name)
        return self.project_ids.get(name)

    def create_project(self, name: str) -> str:
        self.created_projects.append(name)
        project_id = f"proj-{len(self.created_projects)}"
        self.project_ids[name] = project_id
        return project_id

    def find_key(self, project_id: str, name: str) -> str | None:
        self.find_key_calls.append((project_id, name))
        return self.key_ids.get((project_id, name))

    def create_key(self, project_id: str, name: str) -> str:
        self.created_keys.append((project_id, name))
        key_id = f"key-{len(self.created_keys)}"
        self.key_ids[(project_id, name)] = key_id
        return key_id


def test_ensure_project_returns_existing_id_without_creating() -> None:
    fake = FakeProvisioning(project_ids={"mine": "p1"})
    ensured = ensure_project(fake, "mine")
    assert (ensured.id, ensured.created) == ("p1", False)
    assert fake.created_projects == []


def test_ensure_project_creates_once_when_missing() -> None:
    fake = FakeProvisioning()
    ensured = ensure_project(fake, "mine")
    assert (ensured.id, ensured.created) == ("proj-1", True)
    assert fake.created_projects == ["mine"]


def test_ensure_key_returns_existing_id_without_creating() -> None:
    fake = FakeProvisioning(key_ids={("p1", "k"): "key-9"})
    ensured = ensure_key(fake, "p1", "k")
    assert (ensured.id, ensured.created) == ("key-9", False)
    assert fake.created_keys == []


def test_ensure_key_creates_once_when_missing() -> None:
    fake = FakeProvisioning()
    ensured = ensure_key(fake, "p1", "k")
    assert (ensured.id, ensured.created) == ("key-1", True)
    assert fake.created_keys == [("p1", "k")]


def test_second_ensure_run_finds_the_created_id_without_recreating() -> None:
    fake = FakeProvisioning()
    first = ensure_project(fake, "mine")
    second = ensure_project(fake, "mine")
    assert (first.id, first.created) == ("proj-1", True)
    assert (second.id, second.created) == ("proj-1", False)
    assert fake.created_projects == ["mine"]
    # The finder ran again: a caching ensure would hide a backend rename.
    assert fake.find_project_calls == ["mine", "mine"]
    first_key = ensure_key(fake, first.id, "k")
    second_key = ensure_key(fake, first.id, "k")
    assert (first_key.id, second_key.id) == ("key-1", "key-1")
    assert first_key.created is True
    assert second_key.created is False
    assert fake.created_keys == [("proj-1", "k")]
    assert fake.find_key_calls == [("proj-1", "k"), ("proj-1", "k")]


def test_ensure_project_propagates_finder_errors_unwrapped() -> None:
    class ExplodingFinder:
        def find_project(self, name: str) -> str | None:
            raise KmsError("finder exploded")

    with pytest.raises(KmsError, match="finder exploded"):
        ensure_project(ExplodingFinder(), "mine")


def test_ensure_project_propagates_the_adapter_ambiguity_error() -> None:
    # Two exact-name matches: find_project raises; ensure must not retry
    # or swallow, the operator has to clean up duplicates.
    class AmbiguousTransport:
        def request(self, method: str, path: str, json: dict | None = None) -> dict:
            return {"projects": [{"id": "p1", "name": "dupe"}, {"id": "p2", "name": "dupe"}]}

    from kms.infisical_provisioner import InfisicalProvisioner

    provisioner = InfisicalProvisioner("http://127.0.0.1:1", "unused-token")
    provisioner._transport = AmbiguousTransport()
    with pytest.raises(KmsError, match="dupe"):
        ensure_project(provisioner, "dupe")
