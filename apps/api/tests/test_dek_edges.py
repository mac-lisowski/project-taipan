"""Edge-adapter tests: Postgres DekStore and Redis DekCache, no KMS.

The store tests need the app_test Postgres and skip when it is down,
same convention as conftest. The cache tests use the live test Redis
when reachable and a contract fake otherwise.
"""

import base64
import logging
import os
import uuid

import pytest
from api.dek_cache import LocalTtlDekCache, RedisDekCache, TwoTierDekCache
from api.dek_store import PostgresDekStore
from api.field_crypto import build_field_crypto
from api.models import TenantDek
from crypto import FieldCrypto
from kms import InfisicalCipher
from redis import Redis, RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"
REDIS_URL = os.environ.get("API_REDIS_URL", "redis://localhost:6379/0")


def unique_tenant() -> str:
    # Rows survive across session-scoped tests; a fresh tenant isolates each.
    return uuid.uuid4().hex


@pytest.fixture
def store_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def store(store_factory) -> PostgresDekStore:
    return PostgresDekStore(store_factory, KEY_ID)


def count_rows(engine, tenant_id: str) -> int:
    with engine.connect() as conn:
        rows = (
            conn.execute(select(TenantDek).where(TenantDek.tenant_id == tenant_id)).scalars().all()
        )
    return len(rows)


def test_dek_store_roundtrip(store: PostgresDekStore) -> None:
    tenant = unique_tenant()
    stored = store.put(tenant, "wrapped-1-xxxxxxxxxxxxxxxxxxxxxxxx")
    assert stored == "wrapped-1-xxxxxxxxxxxxxxxxxxxxxxxx"
    assert store.get(tenant) == "wrapped-1-xxxxxxxxxxxxxxxxxxxxxxxx"
    assert store.get(unique_tenant()) is None


def test_dek_store_race_adopts_winner(store_factory, store: PostgresDekStore) -> None:
    tenant = unique_tenant()
    winner = store.put(tenant, "wrapped-winner-xxxxxxxxxxxxxxxxxxxxxxxx")
    # A second store inserts its own proposal after the winner landed.
    loser = PostgresDekStore(store_factory, KEY_ID)
    adopted = loser.put(tenant, "wrapped-loser-xxxxxxxxxxxxxxxxxxxxxxxx")
    assert winner == "wrapped-winner-xxxxxxxxxxxxxxxxxxxxxxxx"
    assert adopted == winner
    assert store.get(tenant) == winner
    assert loser.get(tenant) == winner


def test_dek_store_uniqueness(store: PostgresDekStore, engine) -> None:
    tenant = unique_tenant()
    store.put(tenant, "wrapped-1-xxxxxxxxxxxxxxxxxxxxxxxx")
    store.put(tenant, "wrapped-2-xxxxxxxxxxxxxxxxxxxxxxxx")
    assert count_rows(engine, tenant) == 1


@pytest.fixture
def live_redis() -> Redis:
    client = Redis.from_url(REDIS_URL)
    try:
        client.ping()
    except RedisError:
        pytest.skip("redis not running")
    yield client
    client.close()


def test_dek_cache_honors_ttl(live_redis: Redis) -> None:
    cache = RedisDekCache(live_redis, ttl_seconds=900)
    tenant = unique_tenant()
    cache.put(tenant, b"dek-bytes", ttl_seconds=1)
    assert cache.get(tenant) == b"dek-bytes"
    # The fake-clock tests own expiry math; this pins that the real Redis
    # entry carries the caller's per-call TTL instead of the default.
    assert 0 < live_redis.ttl("crypto:dek:" + tenant) <= 1


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRedis:
    """Same set/get contract as redis.Redis, expiry judged by a fake clock."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.values: dict[str, tuple[bytes, float | None]] = {}
        self.get_calls = 0

    def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        expire_at = self.clock.now + ex if ex is not None else None
        self.values[key] = (value, expire_at)

    def get(self, key: str) -> bytes | None:
        self.get_calls += 1
        item = self.values.get(key)
        if item is None:
            return None
        value, expire_at = item
        if expire_at is not None and self.clock.now >= expire_at:
            del self.values[key]
            return None
        return value


def test_dek_cache_ttl_contract_on_fake() -> None:
    clock = FakeClock()
    cache = RedisDekCache(FakeRedis(clock), ttl_seconds=60)
    tenant = unique_tenant()
    cache.put(tenant, b"dek-bytes", ttl_seconds=0)
    assert cache.get(tenant) == b"dek-bytes"
    clock.advance(59)
    assert cache.get(tenant) == b"dek-bytes"
    clock.advance(1)
    assert cache.get(tenant) is None


def test_dek_cache_per_call_ttl_overrides_default_on_fake() -> None:
    clock = FakeClock()
    cache = RedisDekCache(FakeRedis(clock), ttl_seconds=60)
    tenant = unique_tenant()
    cache.put(tenant, b"dek-bytes", ttl_seconds=1)
    assert cache.get(tenant) == b"dek-bytes"
    clock.advance(0.5)
    assert cache.get(tenant) == b"dek-bytes"
    clock.advance(0.5)
    assert cache.get(tenant) is None


def test_two_tier_serves_l1_without_redis_get() -> None:
    clock = FakeClock()
    redis_fake = FakeRedis(clock)
    cache = TwoTierDekCache(LocalTtlDekCache(60), RedisDekCache(redis_fake, ttl_seconds=60))
    tenant = unique_tenant()
    cache.put(tenant, b"dek-bytes", ttl_seconds=0)
    assert redis_fake.get_calls == 0
    assert cache.get(tenant) == b"dek-bytes"
    assert redis_fake.get_calls == 0


def test_two_tier_fills_l1_on_redis_hit() -> None:
    clock = FakeClock()
    redis_fake = FakeRedis(clock)
    tenant = unique_tenant()
    RedisDekCache(redis_fake, ttl_seconds=60).put(tenant, b"dek-bytes", ttl_seconds=0)
    cache = TwoTierDekCache(LocalTtlDekCache(60), RedisDekCache(redis_fake, ttl_seconds=60))
    assert cache.get(tenant) == b"dek-bytes"
    assert redis_fake.get_calls == 1
    # The second read is served from the L1 the first read filled.
    assert cache.get(tenant) == b"dek-bytes"
    assert redis_fake.get_calls == 1


def test_two_tier_l1_expiry_refills_from_redis() -> None:
    clock = FakeClock()
    redis_fake = FakeRedis(clock)
    tenant = unique_tenant()
    local = LocalTtlDekCache(60, monotonic=lambda: clock.now)
    cache = TwoTierDekCache(local, RedisDekCache(redis_fake, ttl_seconds=900))
    cache.put(tenant, b"dek-bytes", ttl_seconds=0)
    clock.advance(61)
    assert cache.get(tenant) == b"dek-bytes"
    assert redis_fake.get_calls == 1


def test_two_tier_serves_cached_dek_while_redis_is_down() -> None:
    cache = TwoTierDekCache(LocalTtlDekCache(60), RedisDekCache(ExplodingRedis(), ttl_seconds=60))
    tenant = unique_tenant()
    cache.put(tenant, b"dek-bytes", ttl_seconds=0)
    assert cache.get(tenant) == b"dek-bytes"


class ExplodingRedis:
    """Every backend call raises, standing in for Redis downtime."""

    def get(self, key: str) -> bytes:
        raise RedisError("connection refused")

    def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        raise RedisError("connection refused")


def test_dek_cache_errors_degrade(caplog) -> None:
    tenant = unique_tenant()
    cache = RedisDekCache(ExplodingRedis(), ttl_seconds=60)
    with caplog.at_level(logging.WARNING):
        assert cache.get(tenant) is None
    get_warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(get_warnings) == 1, "a failed cache read must log exactly one warning"
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        cache.put(tenant, b"dek-bytes", ttl_seconds=60)
    put_warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(put_warnings) == 1, "a failed cache write must log exactly one warning"
    assert tenant not in caplog.text


class StubCipher:
    """Base64 wrap/unwrap, so the degrade test needs no backend."""

    def encrypt(self, key_id: str, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        return base64.urlsafe_b64decode(ciphertext + "=" * (-len(ciphertext) % 4))


class MapStore:
    """In-memory DekStore stand-in, so the degrade test needs no database."""

    def __init__(self) -> None:
        self.rows: dict[str, str] = {}

    def get(self, tenant_id: str) -> str | None:
        return self.rows.get(tenant_id)

    def put(self, tenant_id: str, wrapped_dek: str) -> str:
        self.rows[tenant_id] = wrapped_dek
        return wrapped_dek


def test_raising_cache_does_not_fail_encryption(caplog) -> None:
    module = FieldCrypto(
        cipher=StubCipher(),
        store=MapStore(),
        default_key_id=KEY_ID,
        cache=RedisDekCache(ExplodingRedis(), ttl_seconds=60),
    )
    tenant = unique_tenant()
    with caplog.at_level(logging.WARNING):
        envelope = module.encrypt(tenant, "secret")
    assert module.decrypt(tenant, envelope) == "secret"
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert tenant not in caplog.text


def test_build_field_crypto_requires_infisical_config(monkeypatch) -> None:
    monkeypatch.delenv("API_INFISICAL_TOKEN", raising=False)
    monkeypatch.delenv("API_INFISICAL_KMS_KEY_ID", raising=False)
    assert build_field_crypto() is None


def test_build_field_crypto_wires_real_edges(monkeypatch) -> None:
    # Pin every var the builder reads so ambient env cannot flip the result.
    monkeypatch.setenv("API_INFISICAL_TOKEN", "test-token")
    monkeypatch.setenv("API_INFISICAL_KMS_KEY_ID", KEY_ID)
    monkeypatch.delenv("API_INFISICAL_URL", raising=False)
    monkeypatch.delenv("API_REDIS_URL", raising=False)
    monkeypatch.delenv("API_DEK_CACHE_TTL", raising=False)
    monkeypatch.delenv("API_DEK_CACHE_L1_TTL", raising=False)
    module = build_field_crypto()
    assert isinstance(module, FieldCrypto)
    assert isinstance(module.cipher, InfisicalCipher)
    cache = module.cache
    assert isinstance(cache, TwoTierDekCache)
    assert isinstance(cache.remote, RedisDekCache)
