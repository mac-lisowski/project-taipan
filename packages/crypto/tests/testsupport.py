"""Stubbed edges for the crypto unit tests. No network, no real KMS."""

import base64
import time

from crypto import DefaultKeyResolver, FieldCrypto, KeyResolver
from kms import KmsError


class InMemoryDekCache:
    """Process-local cache. TTL is ignored; the DEK lives for the process.

    Test support only: production uses the two-tier api cache or no cache.
    """

    def __init__(self) -> None:
        self._deks: dict[str, bytes] = {}

    def get(self, tenant_id: str) -> bytes | None:
        return self._deks.get(tenant_id)

    def put(self, tenant_id: str, dek: bytes) -> None:
        self._deks[tenant_id] = dek


DEFAULT_KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"
TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64u_read(text: str) -> bytes:
    return base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_")


def flip_ciphertext_byte(envelope: str) -> str:
    """The envelope with one plaintext-independent ciphertext byte flipped."""
    version, key_id, nonce, ciphertext = envelope.split(":")
    raw = bytearray(b64u_read(ciphertext))
    raw[0] ^= 1
    return f"{version}:{key_id}:{nonce}:{b64u(bytes(raw))}"


class FakeCipher:
    """In-memory Cipher: base64 wrapping, counted calls, injectable unwrap failures."""

    def __init__(self, unwrap_delay: float = 0.0) -> None:
        self.wrap_calls = 0
        self.unwrap_calls = 0
        self.unwrap_failures_left = 0
        self._unwrap_delay = unwrap_delay

    def encrypt(self, key_id: str, data: bytes) -> str:
        self.wrap_calls += 1
        return b64u(data)

    def decrypt(self, key_id: str, ciphertext: str) -> bytes:
        self.unwrap_calls += 1
        if self._unwrap_delay:
            # Yields the GIL so concurrent callers really overlap.
            time.sleep(self._unwrap_delay)
        if self.unwrap_failures_left > 0:
            self.unwrap_failures_left -= 1
            raise KmsError("unwrap rejected by the backend")
        return b64u_read(ciphertext)


class FakeDekStore:
    """Dict-backed DekStore; put can be rigged so the caller always loses the race."""

    def __init__(self, conflict_wrapped: str | None = None) -> None:
        self.rows: dict[str, str] = {}
        self.get_calls = 0
        self.put_calls = 0
        self._conflict_wrapped = conflict_wrapped

    def get(self, tenant_id: str) -> str | None:
        self.get_calls += 1
        return self.rows.get(tenant_id)

    def put(self, tenant_id: str, wrapped_dek: str) -> str:
        self.put_calls += 1
        stored = self._conflict_wrapped or wrapped_dek
        self.rows[tenant_id] = stored
        return stored


class MapResolver:
    """Resolver with per-tenant overrides, to expose the default fallback."""

    def __init__(self, default_key_id: str, overrides: dict[str, str]) -> None:
        self._default = default_key_id
        self._overrides = overrides

    def key_id_for(self, tenant_id: str) -> str:
        return self._overrides.get(tenant_id, self._default)


def make_module(
    store: FakeDekStore | None = None,
    cipher: FakeCipher | None = None,
    resolver: KeyResolver | None = None,
) -> FieldCrypto:
    # The explicit cache keeps the module-level tests about caching honest;
    # a bare FieldCrypto would now mean unwrap-per-use.
    return FieldCrypto(
        cipher=cipher or FakeCipher(),
        store=store or FakeDekStore(),
        resolver=resolver or DefaultKeyResolver(DEFAULT_KEY_ID),
        cache=InMemoryDekCache(),
    )
