"""Thread shares over HTTP: owner create/revoke, public frozen snapshot."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from api import sessions
from api.chat import threads
from api.models import ChatThread, ChatThreadShare
from api_testsupport import admit_user, create_share, create_thread, login, signin
from crypto import tenant_scope
from sqlalchemy import func, select


def _append_message(session_factory, thread_id: str, message: dict) -> None:
    """Append behind the API's back; exercises the frozen-snapshot rule."""
    with session_factory() as db:
        row = db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)))
        # Tenant-carrying writes must flush inside the row's own scope.
        with tenant_scope(row.tenant_id):
            threads.append_message(db, row, message)
        db.commit()


def test_create_returns_token_and_public_read_serves_snapshot(client):
    signin(client, "sharer@x.com")
    thread = create_thread(
        client,
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    )

    body = create_share(client, thread["id"])

    assert set(body) == {"token", "path"}
    assert body["path"] == f"/share/{body['token']}"
    # Dropping the cookie proves the public read needs no session.
    client.cookies.clear()
    resp = client.get(f"/api/public/threads/{body['token']}")
    assert resp.status_code == 200
    assert resp.json() == {
        "title": "hello",
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
    }


def test_snapshot_freezes_at_create_time(client, session_factory):
    signin(client, "freezer@x.com")
    thread = create_thread(client, {"role": "user", "content": "first"})
    token = create_share(client, thread["id"])["token"]
    _append_message(session_factory, thread["id"], {"role": "user", "content": "second"})

    resp = client.get(f"/api/public/threads/{token}")

    assert resp.status_code == 200
    assert [m["content"] for m in resp.json()["messages"]] == ["first"]


def test_repeat_create_keeps_token_and_refreshes_snapshot(client, session_factory):
    signin(client, "refresh@x.com")
    thread = create_thread(client, {"role": "user", "content": "v1"})
    first = create_share(client, thread["id"])
    _append_message(session_factory, thread["id"], {"role": "assistant", "content": "v2"})

    second = create_share(client, thread["id"])

    assert second["token"] == first["token"]
    resp = client.get(f"/api/public/threads/{first['token']}")
    assert [m["content"] for m in resp.json()["messages"]] == ["v1", "v2"]


def test_revoke_404s_public_read_and_recreate_mints_fresh_token(client, session_factory):
    signin(client, "revoker@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    first = create_share(client, thread["id"])["token"]

    assert client.delete(f"/api/threads/shares/delete/{thread['id']}").status_code == 204
    assert client.get(f"/api/public/threads/{first}").status_code == 404

    second = create_share(client, thread["id"])["token"]
    assert second != first
    assert client.get(f"/api/public/threads/{second}").status_code == 200
    assert client.get(f"/api/public/threads/{first}").status_code == 404
    with session_factory() as db:
        # Revoked rows stay behind as audit records.
        assert db.scalar(select(func.count()).select_from(ChatThreadShare)) == 2


def test_revoke_without_live_share_404s(client):
    signin(client, "noshare@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})

    assert client.delete(f"/api/threads/shares/delete/{thread['id']}").status_code == 404


def test_user_b_cannot_share_or_revoke_user_a_thread(client):
    admit_user(client, "alice@x.com")
    admit_user(client, "bob@x.com")
    login(client, "alice@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "alice only"})["id"]
    token = create_share(client, thread_id)["token"]
    login(client, "bob@x.com")

    assert client.post(f"/api/threads/shares/create/{thread_id}").status_code == 404
    assert client.get(f"/api/threads/shares/get/{thread_id}").status_code == 404
    assert client.delete(f"/api/threads/shares/delete/{thread_id}").status_code == 404
    assert client.get(f"/api/public/threads/{token}").status_code == 200


def test_share_endpoints_need_a_session(client):
    thread_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/threads/shares/create/{thread_id}").status_code == 401
    assert client.get(f"/api/threads/shares/get/{thread_id}").status_code == 401
    assert client.delete(f"/api/threads/shares/delete/{thread_id}").status_code == 401
    # The public read carries no session check; a dead token 404s, not 401s.
    assert client.get("/api/public/threads/dead-token").status_code == 404


def test_token_is_stored_hashed(client, session_factory):
    signin(client, "hashed@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    token = create_share(client, thread["id"])["token"]

    with session_factory() as db:
        share = db.scalar(select(ChatThreadShare))

    assert share.token_hash == hashlib.sha256(token.encode()).hexdigest()
    # The plaintext token must not appear in any stored column.
    assert token not in share.token_hash
    assert token not in share.title
    assert token not in json.dumps(share.snapshot)


def test_deleting_thread_removes_share(client, session_factory):
    signin(client, "cascade@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    token = create_share(client, thread["id"])["token"]

    assert client.delete(f"/api/threads/delete/{thread['id']}").status_code == 204
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ChatThreadShare)) == 0
    assert client.get(f"/api/public/threads/{token}").status_code == 404


def test_expired_share_reads_404(client, session_factory):
    signin(client, "expiry@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    token = create_share(client, thread["id"])["token"]
    with session_factory() as db:
        share = db.scalar(select(ChatThreadShare))
        with tenant_scope(share.tenant_id):
            # A fixed past stamp is deterministic; expiry logic compares in SQL.
            share.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
            db.flush()
        db.commit()

    assert client.get(f"/api/public/threads/{token}").status_code == 404


def test_secret_rotation_rehashes_live_share(client, session_factory, monkeypatch):
    monkeypatch.setenv("API_SHARE_TOKEN_SECRET", "first-secret")
    signin(client, "drift@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    first = create_share(client, thread["id"])["token"]
    with session_factory() as db:
        share_id = db.scalar(select(ChatThreadShare.id))
    monkeypatch.setenv("API_SHARE_TOKEN_SECRET", "second-secret")

    second = create_share(client, thread["id"])["token"]

    assert second != first
    with session_factory() as db:
        rows = db.scalars(select(ChatThreadShare)).all()
    # In-place rehash: the same row keeps its slot; no delete + recreate.
    assert [row.id for row in rows] == [share_id]
    assert rows[0].token_hash == hashlib.sha256(second.encode()).hexdigest()
    assert client.get(f"/api/public/threads/{second}").status_code == 200
    assert client.get(f"/api/public/threads/{first}").status_code == 404


def test_public_payload_is_only_title_and_messages(client):
    signin(client, "minimal@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    token = create_share(client, thread["id"])["token"]

    body = client.get(f"/api/public/threads/{token}").json()

    # No tenant, user, or email keys may leak through the public read.
    assert set(body) == {"title", "messages"}


def test_snapshot_drops_system_rows_and_extra_keys(client, session_factory):
    signin(client, "project@x.com")
    thread = create_thread(
        client,
        {"role": "system", "content": "never leave the api"},
        {"role": "user", "content": "hi", "runId": "r-1", "trace": {"id": 1}},
    )
    # Non-string content (parts arrays) must survive verbatim.
    _append_message(
        session_factory,
        thread["id"],
        {"role": "assistant", "content": [{"type": "text", "text": "part"}]},
    )

    token = create_share(client, thread["id"])["token"]

    assert client.get(f"/api/public/threads/{token}").json()["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [{"type": "text", "text": "part"}]},
    ]


def test_create_after_expiry_retires_the_row_and_mints_fresh(client, session_factory):
    signin(client, "pastdue@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    first = create_share(client, thread["id"])["token"]
    with session_factory() as db:
        stale = db.scalar(select(ChatThreadShare))
        with tenant_scope(stale.tenant_id):
            stale.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
            db.flush()
        db.commit()

    second = create_share(client, thread["id"])

    assert second["token"] != first
    assert client.get(f"/api/public/threads/{first}").status_code == 404
    assert client.get(f"/api/public/threads/{second['token']}").status_code == 200
    with session_factory() as db:
        rows = db.scalars(select(ChatThreadShare)).all()
    # The dead row stays as a revoked audit record; the new row is live.
    assert len(rows) == 2
    assert sum(row.revoked_at is not None for row in rows) == 1


def test_share_ops_404_when_session_tenant_differs(client):
    signin(client, "tencheck@x.com")
    user_id = client.get("/api/auth/me").json()["id"]
    thread = create_thread(client, {"role": "user", "content": "x"})
    token = create_share(client, thread["id"])["token"]
    # A session minted under a foreign tenant must not see this thread.
    client.cookies.set("session", sessions.mint(user_id, "other-tenant"))

    assert client.post(f"/api/threads/shares/create/{thread['id']}").status_code == 404
    assert client.get(f"/api/threads/shares/get/{thread['id']}").status_code == 404
    assert client.delete(f"/api/threads/shares/delete/{thread['id']}").status_code == 404
    # The public read is untouched: the share itself is still live.
    assert client.get(f"/api/public/threads/{token}").status_code == 200


def test_share_status_reports_live_only(client, session_factory):
    signin(client, "status@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    url = f"/api/threads/shares/get/{thread['id']}"

    assert client.get(url).json() == {"shared": False}
    create_share(client, thread["id"])
    assert client.get(url).json() == {"shared": True}
    with session_factory() as db:
        share = db.scalar(select(ChatThreadShare))
        with tenant_scope(share.tenant_id):
            share.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
            db.flush()
        db.commit()

    assert client.get(url).json() == {"shared": False}
    # Revoking the dead row still reports false.
    assert client.delete(f"/api/threads/shares/delete/{thread['id']}").status_code == 204
    assert client.get(url).json() == {"shared": False}
