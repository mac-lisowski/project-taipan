"""ORM-layer tests for the EncryptedString column type.

In-memory SQLite and a stubbed crypto module: no network, no real KMS.
The stub seals every plaintext and marks the envelope with the tenant
it encrypted for, so the stored bytes expose the flush-time scope.
"""

import pytest
from api.models import EncryptedString
from api.models.encrypted_string import get_field_crypto, set_field_crypto
from crypto import CryptoCategory, CryptoError, tenant_scope
from sqlalchemy import Integer, StaticPool, create_engine, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class StubCrypto:
    """Seals plaintext under a tenant-marked envelope; records tenants."""

    def __init__(self) -> None:
        self.sealed: dict[str, str] = {}
        self.count = 0
        self.encrypt_tenants: list[str] = []
        self.decrypt_tenants: list[str] = []

    def encrypt(self, tenant_id: str, plaintext: str) -> str:
        self.encrypt_tenants.append(tenant_id)
        envelope = f"stub::{tenant_id}::{self.count}"
        self.count += 1
        self.sealed[envelope] = plaintext
        return envelope

    def decrypt(self, tenant_id: str, envelope: str) -> str:
        self.decrypt_tenants.append(tenant_id)
        marked = envelope.split("::")[1]
        if marked != tenant_id:
            # The real module fails the tag on a foreign tenant; so does the stub.
            raise CryptoError(CryptoCategory.DECRYPT_FAILURE, "foreign tenant")
        return self.sealed[envelope]


@pytest.fixture
def stub_crypto():
    # Restore whatever was registered, so test order cannot leak state.
    prior = get_field_crypto()
    stub = StubCrypto()
    set_field_crypto(stub)
    yield stub
    set_field_crypto(prior)


class OrmBase(DeclarativeBase):
    pass


class Secret(OrmBase):
    __tablename__ = "orm_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    secret: Mapped[str] = mapped_column(EncryptedString)


@pytest.fixture
def session(stub_crypto):
    # One shared connection: separate checkouts would each get an empty db.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    OrmBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session, engine
    engine.dispose()


def raw_stored(engine, secret_id: int) -> str:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT secret FROM orm_secrets WHERE id = :id"), {"id": secret_id}
        ).scalar_one()


def test_column_roundtrips_through_orm(session, stub_crypto) -> None:
    db, engine = session
    with tenant_scope("tenant-a"):
        row = Secret(secret="alpha secret")
        db.add(row)
        db.flush()
        stored_id = row.id
        # Commit so the raw read cannot roll back the pending insert.
        db.commit()
    # The post-commit re-read runs real SQL, so decrypt actually executes.
    with tenant_scope("tenant-a"):
        assert db.get(Secret, stored_id).secret == "alpha secret"
    # The raw column holds the module's envelope, never the plaintext.
    assert raw_stored(engine, stored_id) == "stub::tenant-a::0"
    assert "alpha" not in raw_stored(engine, stored_id)
    assert stub_crypto.encrypt_tenants == ["tenant-a"]
    assert stub_crypto.decrypt_tenants == ["tenant-a"]


def test_column_outside_tenant_scope_raises(session) -> None:
    db, _ = session
    db.add(Secret(secret="unscooped secret"))
    with pytest.raises(StatementError) as excinfo:
        db.flush()
    # SQLAlchemy wraps bind-time errors; the module error stays the cause.
    assert isinstance(excinfo.value.orig, CryptoError)
    assert excinfo.value.orig.category == CryptoCategory.MISSING_TENANT_SCOPE


def test_column_reads_context_at_flush_time(session, stub_crypto) -> None:
    # One tenant scope per flush: rows added under one scope but flushed
    # under another encrypt under the flush scope, not the add scope.
    db, engine = session
    with tenant_scope("tenant-a"):
        row = Secret(secret="late flush secret")
        db.add(row)
    with tenant_scope("tenant-b"):
        db.flush()
        stored_id = row.id
    db.commit()
    assert raw_stored(engine, stored_id) == "stub::tenant-b::0"
    assert stub_crypto.encrypt_tenants == ["tenant-b"]


def test_column_read_outside_tenant_scope_raises(session) -> None:
    # Decrypt is tenant-bound too: a stored row read back with no scope fails.
    db, _ = session
    with tenant_scope("tenant-a"):
        row = Secret(secret="scoped secret")
        db.add(row)
        db.flush()
        stored_id = row.id
    db.expunge_all()
    with pytest.raises(CryptoError) as excinfo:
        db.get(Secret, stored_id)
    assert excinfo.value.category == CryptoCategory.MISSING_TENANT_SCOPE
