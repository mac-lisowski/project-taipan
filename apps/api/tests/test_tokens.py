"""Tokens service seam: mint, mint_single, verify, burn through injected fakes."""

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
    mint_single,
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

    def delete(self, key: str) -> None:
        self.entries.pop(key, None)


class ContendedStore(RecordingStore):
    """Fake that always loses the atomic swap, as under a racing verify."""

    def __init__(self) -> None:
        super().__init__()
        self.swap_attempted = False

    def set_if_unchanged(self, key: str, expected: str, value: str, ttl_seconds: int) -> bool:
        self.swap_attempted = True
        return False


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
    before = dict(store.entries)
    # Losing the swap means a concurrent verify consumed the token first.
    with pytest.raises(TokenAlreadyUsed):
        verify(token, PURPOSE_RESET, store=store)
    assert store.swap_attempted is True
    # The loser must not write; the at-rest record stays untouched.
    assert store.entries == before


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
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    # The store port has no scan, so the mint's single entry is the only
    # place a corrupt record can be planted at the real key.
    [key] = store.entries
    for bad in ("not-json", json.dumps([7, "reset", False])):
        store.entries[key] = bad
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


def test_raw_token_is_never_stored_at_rest():
    # The at-rest key format is tokens' private detail; the pin is only
    # that the raw token appears in no stored key or value.
    store = RecordingStore()
    token = mint(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    assert len(store.entries) == 1
    assert all(token not in k and token not in v for k, v in store.entries.items())


def test_purpose_stays_open_to_new_values():
    store = RecordingStore()
    token = mint(user_id=7, purpose="magic-link", ttl_seconds=600, store=store)
    data = verify(token, "magic-link", store=store)
    assert data.purpose == "magic-link"


def test_mint_single_kills_the_old_link():
    store = RecordingStore()
    old = mint_single(user_id=7, purpose=PURPOSE_ACTIVATION, ttl_seconds=600, store=store)
    new = mint_single(user_id=7, purpose=PURPOSE_ACTIVATION, ttl_seconds=600, store=store)
    with pytest.raises(TokenNotFound):
        verify(old, PURPOSE_ACTIVATION, store=store)
    data = verify(new, PURPOSE_ACTIVATION, store=store)
    assert data.user_id == 7
    assert data.purpose == PURPOSE_ACTIVATION


def test_mint_single_leaves_other_users_and_purposes_live():
    store = RecordingStore()
    keep = mint_single(user_id=7, purpose=PURPOSE_ACTIVATION, ttl_seconds=600, store=store)
    mint_single(user_id=8, purpose=PURPOSE_ACTIVATION, ttl_seconds=600, store=store)
    mint_single(user_id=7, purpose=PURPOSE_RESET, ttl_seconds=600, store=store)
    assert verify(keep, PURPOSE_ACTIVATION, store=store).user_id == 7


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
