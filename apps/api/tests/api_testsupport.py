"""Shared fakes, constants, and route helpers for the api tests.

No network, no real KMS. Helpers live here, not in conftest, so test
modules never import the bare name `conftest` (every tests dir's
conftest competes for that one module name; importing it is
collection-order luck).
"""

import base64
import os
import uuid
from pathlib import Path

import httpx2
from api.chat.models import ModelCatalog
from api.models import Role, UserTenant, UserTenantRole
from crypto import tenant_scope
from sqlalchemy import select

KEY_ID = "5f0c9a1e-2222-4333-8444-555566667777"

DEFAULT_CHAT_MODEL = "gpt-4o-mini"
CHAT_MODELS_LISTING = {"data": [{"id": "gpt-4o-mini"}, {"id": "llama-3"}]}

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"

# Test databases are the suite's business, not production Config's.
# Read at import so docker/devcontainer env overrides keep working.
TEST_ADMIN_URL = os.environ.get(
    "API_TEST_ADMIN_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)
TEST_URL = os.environ.get(
    "API_TEST_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/app_test",
)


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


def create_user(client, email: str, password: str = "s3cret123") -> int:
    """Create a user through the gated route; caller holds an admin session."""
    resp = client.post("/api/users", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()["id"]


def grant_tenant_admin(session_factory, user_id: int) -> None:
    """Grant the admin tenant role in the user's personal tenant; no owner role."""
    with session_factory() as session:
        tenant_id = session.scalar(
            select(UserTenant.tenant_id).where(UserTenant.user_id == user_id)
        )
        # Tenant-carrying writes must flush inside the scope they point at.
        with tenant_scope(tenant_id):
            session.add(UserTenantRole(user_id=user_id, tenant_id=tenant_id, role=Role.ADMIN))
            session.flush()
        session.commit()


def setup_admin(client, email: str = "admin@x.com", password: str = "s3cret123") -> int:
    """Run POST setup once; returns the admin user id."""
    resp = client.post("/api/setup", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()["id"]


def login(client, email: str, password: str = "s3cret123") -> str:
    """Log in; returns the session cookie for manual request building."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 204
    token = resp.cookies.get("session")
    assert token is not None
    return token


def admit_user(client, email: str, password: str = "s3cret123") -> None:
    """Create the user, running setup first when the instance is fresh."""
    if client.get("/api/setup").json()["needs_setup"]:
        setup_admin(client)
    create_user(client, email, password)


def signin(client, email: str, password: str = "s3cret123") -> None:
    """Admit then log in; the standard chat-test entry."""
    admit_user(client, email, password)
    login(client, email, password)


def create_thread(client, *messages) -> dict:
    """POST threads/create; returns the boundary Thread body."""
    resp = client.post("/api/threads/create", json={"messages": list(messages)})
    assert resp.status_code == 200
    return resp.json()


def create_share(client, thread_id: str) -> dict:
    """POST threads/shares/create; returns the boundary share body."""
    resp = client.post(f"/api/threads/shares/create/{thread_id}")
    assert resp.status_code == 200
    return resp.json()


def model_catalog(handler, *, ttl_seconds=60, clock=None, default=DEFAULT_CHAT_MODEL):
    """A ModelCatalog on a MockTransport, shared by listing and completion tests."""
    return ModelCatalog(
        "http://gw.local:4000",
        "secret-key",
        default,
        ttl_seconds,
        transport=httpx2.MockTransport(handler),
        clock=clock or FakeClock(),
    )
