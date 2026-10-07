"""Tokens service seam: mint, verify, burn through injected fakes."""

import hashlib
import json

import pytest
from api.kvstore import TOKEN_KEYS, MemoryKVStore
from api.tokens import (
    PURPOSE_ACTIVATION,
    PURPOSE_RESET,
    TokenAlreadyUsed,
    TokenNotFound,
    TokenPurposeMismatch,
    burn,
    mint,
    verify,
)
from api_testsupport import FakeClock


class RecordingStore:
    """Fake that keeps every written value for at-rest inspection."""

    def __init__(self) -> None:
        self.entries: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.entries.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.entries[key] = value

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        if self.entries.get(key) != expected:
            return False
        self.entries[key] = value
        return True


class ContendedStore(RecordingStore):
    """Fake that always loses the atomic swap, as under a racing verify."""

    def __init__(self) -> None:
        super().__init__()
        self.swap_attempted = False

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        self.swap_attempted = True
        return False


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def test_mint_then_verify_returns_user_and_purpose():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    data = verify(token, PURPOSE_RESET, store=store)
    assert data.user_id == 7
    assert data.purpose == PURPOSE_RESET


def test_verify_is_single_use():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    verify(token, PURPOSE_RESET, store=store)
    with pytest.raises(TokenAlreadyUsed):
        verify(token, PURPOSE_RESET, store=store)


def test_verify_marks_used_through_atomic_swap_only():
    store = ContendedStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    # Losing the swap means a concurrent verify consumed the token first.
    with pytest.raises(TokenAlreadyUsed):
        verify(token, PURPOSE_RESET, store=store)
    assert store.swap_attempted is True
    # The loser must not write; the record still reads as unused.
    assert '"used": false' in store.entries[digest(token)]


def test_reset_token_never_verifies_as_activation():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    with pytest.raises(TokenPurposeMismatch):
        verify(token, PURPOSE_ACTIVATION, store=store)


def test_tampered_token_fails():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    with pytest.raises(TokenNotFound):
        verify(token + "x", PURPOSE_RESET, store=store)


def test_corrupt_record_raises_token_not_found():
    store = MemoryKVStore(TOKEN_KEYS)
    token = "record-corrupted-in-store"
    key = digest(token)

    # Not JSON at all
    store.set(key, "not-json", ttl_seconds=600)
    with pytest.raises(TokenNotFound, match="corrupt"):
        verify(token, PURPOSE_RESET, store=store)

    # Valid JSON, but not our record shape
    store.set(key, json.dumps([7, "reset", False]), ttl_seconds=600)
    with pytest.raises(TokenNotFound, match="corrupt"):
        verify(token, PURPOSE_RESET, store=store)


def test_expired_token_fails():
    clock = FakeClock()
    store = MemoryKVStore(TOKEN_KEYS, clock=clock)
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=30, store=store)
    clock.advance(31)
    with pytest.raises(TokenNotFound):
        verify(token, PURPOSE_RESET, store=store)


def test_burn_then_verify_fails_as_used():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    burn(token, store=store)
    with pytest.raises(TokenAlreadyUsed):
        verify(token, PURPOSE_RESET, store=store)


def test_burn_unknown_token_changes_nothing():
    store = RecordingStore()
    burn("no-such-token", store=store)
    assert store.entries == {}


def test_store_holds_hash_never_raw_token():
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    assert list(store.entries) == [digest(token)]
    assert token not in store.entries[digest(token)]


def test_purpose_stays_open_to_new_values():
    store = RecordingStore()
    token = mint(user_id=7, purpose="magic-link", ttl_seconds=600, store=store)
    data = verify(token, "magic-link", store=store)
    assert data.purpose == "magic-link"


def test_consumed_token_is_reclaimed_after_grace_ttl():
    clock = FakeClock()
    store = MemoryKVStore(TOKEN_KEYS, clock=clock)
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    verify(token, PURPOSE_RESET, store=store)
    # Past the grace window but well inside the original ttl the record
    # must be gone, so a late verify reads as unknown, not as used.
    clock.advance(61)
    with pytest.raises(TokenNotFound):
        verify(token, PURPOSE_RESET, store=store)


def test_mint_rejects_nonpositive_ttl():
    store = RecordingStore()
    with pytest.raises(ValueError):
        mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=0, store=store)
