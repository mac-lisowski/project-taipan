"""Token store wiring: the shared singleton and its Redis builder.

Records are keyed by token hash; the KV port supplies the storage
behaviors, so this module only decides the keyspace.
"""

from __future__ import annotations

from redis import Redis

from api.config import get_config
from api.kvstore import TOKEN_KEYS, KVStore, RedisKVStore

_token_store: KVStore | None = None


def build_token_store() -> RedisKVStore:
    """Build production Redis token store from configuration."""
    client = Redis.from_url(get_config().store.redis_url)
    # Own namespace keeps token digests out of the session keyspace.
    return RedisKVStore(client, namespace=TOKEN_KEYS)


def get_token_store() -> KVStore:
    """Return the shared token store, initializing the Redis adapter if unset."""
    global _token_store
    if _token_store is None:
        _token_store = build_token_store()
    return _token_store


def set_token_store(store: KVStore | None) -> None:
    """Set the shared token store for testing or lifecycle wiring."""
    global _token_store
    _token_store = store
