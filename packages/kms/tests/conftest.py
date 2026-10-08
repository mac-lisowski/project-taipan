"""Shared fixtures for the kms suite.

Live tests carry the `live_only` mark from kms_testsupport and skip when
Infisical is unreachable or the token is unset. Structural and
transport tests run everywhere. The fixture self-provisions a
throwaway KMS project and key, then deletes the project on teardown.
"""

import uuid
from collections.abc import Iterator
from typing import NamedTuple

import pytest
from kms import KmsError
from kms.infisical_cipher import InfisicalCipher
from kms.infisical_provisioner import InfisicalProvisioner
from kms_testsupport import INFISICAL_URL, TOKEN


class Keys(NamedTuple):
    provisioner: InfisicalProvisioner
    cipher: InfisicalCipher
    project_id: str
    project_name: str
    key_a: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    provisioner = InfisicalProvisioner(INFISICAL_URL, TOKEN)
    cipher = InfisicalCipher(INFISICAL_URL, TOKEN)
    project_name = f"taipan-test-{uuid.uuid4().hex}"
    project_id = provisioner.create_project(project_name)
    key_a = provisioner.create_key(project_id, "test-key-a")
    yield Keys(provisioner, cipher, project_id, project_name, key_a)
    try:
        provisioner.delete_project(project_id)
    except KmsError as exc:
        # A lost-response retry 404s; the project is gone either way.
        if exc.status_code != 404:
            raise
