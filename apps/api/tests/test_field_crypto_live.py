"""Live proof: the whole chain against real Infisical.

Skip when the instance is unreachable or no admin token is set, same
convention as test_infisical_kms.py. The fixture self-provisions a KMS
project and key through the provisioner, then deletes the project on
teardown. The transport-failure test needs no live instance and never
skips.
"""

import os
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from typing import NamedTuple

import pytest
from api.dek_cache import (
    KEY_PREFIX,
    LocalTtlDekCache,
    RedisDekCache,
    TwoTierDekCache,
)
from api.dek_store import PostgresDekStore
from api.field_crypto import DEFAULT_DEK_CACHE_TTL_SECONDS, DEFAULT_DEK_L1_TTL_SECONDS
from api_testsupport import KEY_ID, unique_tenant
from crypto import NONCE_BYTES, CryptoCategory, CryptoError, FieldCrypto, parse
from kms import KmsError
from kms.infisical_cipher import InfisicalCipher
from kms.infisical_provisioner import InfisicalProvisioner
from redis import Redis
from sqlalchemy.orm import sessionmaker

INFISICAL_URL = os.environ.get("API_INFISICAL_URL", "http://localhost:8080")
TOKEN = os.environ.get("API_INFISICAL_TOKEN", "")
REDIS_URL = os.environ.get("API_REDIS_URL", "redis://localhost:6379/0")


def _reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{INFISICAL_URL}/api/status", timeout=2) as r:
            return r.status == 200
    except (OSError, urllib.error.URLError):
        return False


live_only = pytest.mark.skipif(
    not _reachable() or not TOKEN, reason="infisical not reachable or token unset"
)


class Keys(NamedTuple):
    provisioner: InfisicalProvisioner
    key_id: str


@pytest.fixture(scope="session")
def keys() -> Iterator[Keys]:
    provisioner = InfisicalProvisioner(INFISICAL_URL, TOKEN)
    project_id = provisioner.create_project(f"taipan-test-{uuid.uuid4().hex}")
    try:
        key_id = provisioner.create_key(project_id, "test-field-key")
    except BaseException:
        # Setup failure would otherwise leak the live project forever.
        provisioner.delete_project(project_id)
        raise
    yield Keys(provisioner, key_id)
    try:
        provisioner.delete_project(project_id)
    except KmsError as exc:
        # A lost-response retry 404s; the project is gone either way.
        if " failed: 404 " not in str(exc):
            raise


def make_module(key_id: str, engine) -> FieldCrypto:
    """A fresh FieldCrypto wired like production; no shared warm state."""
    store = PostgresDekStore(sessionmaker(bind=engine, expire_on_commit=False), key_id)
    cache = TwoTierDekCache(
        local=LocalTtlDekCache(DEFAULT_DEK_L1_TTL_SECONDS),
        remote=RedisDekCache(Redis.from_url(REDIS_URL), ttl_seconds=DEFAULT_DEK_CACHE_TTL_SECONDS),
    )
    cipher = InfisicalCipher(INFISICAL_URL, TOKEN)
    return FieldCrypto(cipher=cipher, store=store, default_key_id=key_id, cache=cache)


def drop_dek_cache(tenant_id: str) -> int:
    """Drop the Redis DEK entry; the count proves the cold path was real."""
    with Redis.from_url(REDIS_URL) as client:
        return client.delete(KEY_PREFIX + tenant_id)


@live_only
def test_live_full_chain_roundtrip(keys: Keys, engine) -> None:
    tenant = unique_tenant()
    module = make_module(keys.key_id, engine)
    plaintext = "live chain secret"
    envelope = module.encrypt(tenant, plaintext)
    # The stored form parses as the versioned envelope and hides the plaintext.
    key_id, nonce, _ciphertext = parse(envelope)
    assert key_id == keys.key_id
    assert len(nonce) == NONCE_BYTES
    assert plaintext not in envelope
    # A cold module: fresh instance and a proven-dropped cache entry, so
    # the decrypt must unwrap the Postgres-stored DEK through live Infisical.
    cold = make_module(keys.key_id, engine)
    assert drop_dek_cache(tenant) == 1
    assert cold.decrypt(tenant, envelope) == plaintext


@live_only
def test_live_rotate_then_unwrap(keys: Keys, engine) -> None:
    tenant = unique_tenant()
    module = make_module(keys.key_id, engine)
    plaintext = "rotation secret"
    envelope = module.encrypt(tenant, plaintext)
    keys.provisioner.rotate(keys.key_id)
    # The wrapped DEK predates the rotation: versioned keys must keep
    # it unwrappable so rotation never needs a data migration.
    cold = make_module(keys.key_id, engine)
    assert drop_dek_cache(tenant) == 1
    assert cold.decrypt(tenant, envelope) == plaintext


def test_live_transport_failure_maps_to_module_error() -> None:
    # A dead endpoint must surface as the module error, never transport.
    class DeadStore:
        def get(self, tenant_id: str) -> str | None:
            return None

        def put(self, tenant_id: str, wrapped_dek: str) -> str:
            return wrapped_dek

    module = FieldCrypto(
        cipher=InfisicalCipher("http://127.0.0.1:1", "unused-token"),
        store=DeadStore(),
        default_key_id=KEY_ID,
    )
    with pytest.raises(CryptoError) as excinfo:
        module.encrypt("some-tenant", "secret")
    assert excinfo.value.category == CryptoCategory.WRAP_FAILURE
