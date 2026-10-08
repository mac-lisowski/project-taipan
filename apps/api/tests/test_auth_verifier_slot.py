"""Auth router mapping through the verifier slot. No password rules here."""

from types import SimpleNamespace

from api.main import app
from api.verifiers import get_credential_verifier
from api_testsupport import setup_admin
from sqlalchemy.orm import Session


class FakeVerifier:
    """Injected verifier: accepts any password for one known email."""

    def __init__(self, user_id: int, email: str) -> None:
        self.user_id = user_id
        self.email = email
        self.calls: list[tuple[str, str]] = []

    def verify(self, db: Session, email: str, password: str):
        # Body fields must reach the verifier untouched; that is the mapping.
        self.calls.append((email, password))
        if email == self.email:
            return SimpleNamespace(id=self.user_id)
        return None


class RejectingVerifier:
    """Injected verifier: no credential ever verifies."""

    def verify(self, db: Session, email: str, password: str):
        return None


def _override(verifier):
    app.dependency_overrides[get_credential_verifier] = lambda: verifier


def _clear_override():
    app.dependency_overrides.pop(get_credential_verifier, None)


def test_login_issues_session_through_injected_verifier(client, session_factory):
    user_id = setup_admin(client, email="vf@example.com")
    fake = FakeVerifier(user_id, "vf@example.com")
    _override(fake)
    try:
        resp = client.post(
            "/api/auth/login", json={"email": "vf@example.com", "password": "not-the-password"}
        )
    finally:
        _clear_override()
    assert resp.status_code == 204
    assert resp.cookies.get("session") is not None
    assert fake.calls == [("vf@example.com", "not-the-password")]


def test_login_verifier_none_maps_to_401_without_cookie(client):
    setup_admin(client, email="nr@example.com")
    _override(RejectingVerifier())
    try:
        resp = client.post(
            "/api/auth/login", json={"email": "nr@example.com", "password": "s3cret123"}
        )
    finally:
        _clear_override()
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid email or password"
    assert "session" not in resp.headers.get("set-cookie", "")
