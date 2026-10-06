"""Shared fixtures for the kms suite.

Skip-when-down, mirroring apps/api/tests: live tests carry a
`live_only` mark and skip when Infisical is unreachable or the
token is unset. Structural and transport tests run everywhere.
"""

import os
import uuid
from collections.abc import Iterator
from typing import NamedTuple

import pytest
from kms import KmsError
from kms.infisical_cipher import InfisicalCipher
from kms.infisical_provisioner import InfisicalProvisioner

INFISICAL_URL = os.environ.get("API_INFISICAL_URL", "http://localhost:8080")
TOKEN = os.environ.get("API_INFISICAL_TOKEN", "")


class Keys(NamedTuple):
    provisioner: InfisicalProvisioner
    cipher: InfisicalCipher
    project_id: str
    key_a: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    provisioner = InfisicalProvisioner(INFISICAL_URL, TOKEN)
    cipher = InfisicalCipher(INFISICAL_URL, TOKEN)
    project_id = provisioner.create_project(f"taipan-test-{uuid.uuid4().hex}")
    key_a = provisioner.create_key(project_id, "test-key-a")
    yield Keys(provisioner, cipher, project_id, key_a)
    try:
        provisioner.delete_project(project_id)
    except KmsError as exc:
        # A lost-response retry 404s; the project is gone either way.
        if " failed: 404 " not in str(exc):
            raise
