"""Shared fakes and constants for the api tests. No network, no real KMS."""

import base64
import uuid

KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"


def unique_tenant() -> str:
    # Rows survive across session-scoped tests; a fresh tenant isolates each.
    return uuid.uuid4().hex


class StubCipher:
    """Base64 wrap/unwrap, so the degrade test needs no backend."""

    def encrypt(self, key_id: str, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        return base64.urlsafe_b64decode(ciphertext + "=" * (-len(ciphertext) % 4))


class FakeClock:
    """Injectable clock for TTL-sensitive stores and sessions."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# Normalized token shape of the store's CAS Lua. The stub executes only
# this exact shape, so any edit to the real script fails tests here
# instead of drifting silently from the hardcoded semantics.
_CAS_SCRIPT_SHAPE = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3]) return 1 end return 0"
)


class FakeRedis:
    """Minimal Redis stand-in honoring EX TTLs against a FakeClock."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.data: dict[str, tuple[str | bytes, float | None]] = {}

    def get(self, key: str) -> str | bytes | None:
        if key not in self.data:
            return None
        val, expires_at = self.data[key]
        if expires_at is not None and self.clock.now >= expires_at:
            del self.data[key]
            return None
        return val

    def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        expires_at = self.clock.now + ex if ex is not None else None
        self.data[key] = (value, expires_at)

    def delete(self, key: str) -> int:
        return 1 if self.data.pop(key, None) is not None else 0

    def eval(self, script: str, numkeys: int, *keys_and_args: str | int) -> int:
        """Execute the compare-and-set script; refuse any other script."""
        if " ".join(script.split()) != _CAS_SCRIPT_SHAPE or numkeys != 1:
            raise NotImplementedError("FakeRedis.eval mirrors only the CAS script")
        key, expected, value, ttl = keys_and_args
        if self.get(key) == expected:
            self.set(key, value, ex=int(ttl))
            return 1
        return 0


class MapStore:
    """In-memory DekStore stand-in, so the degrade test needs no database."""

    def __init__(self) -> None:
        self.rows: dict[str, str] = {}

    def get(self, tenant_id: str) -> str | None:
        return self.rows.get(tenant_id)

    def put(self, tenant_id: str, wrapped_dek: str) -> str:
        self.rows[tenant_id] = wrapped_dek
        return wrapped_dek
