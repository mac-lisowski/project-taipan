"""Chat queue over HTTP: enqueue, list, edit, remove, owner scoped."""

import uuid

from api.models import ChatQueuedMessage, UserTenant
from api_testsupport import admit_user, create_thread, login, signin
from sqlalchemy import func, select


def _enqueue(client, thread_id: str, text: str):
    return client.post(
        "/api/threads/queue/create",
        json={"threadId": thread_id, "content": {"text": text}},
    )


def test_enqueue_returns_row_shape_and_list_orders_by_seq(client):
    signin(client, "enq@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]

    first = _enqueue(client, thread_id, "one")
    second = _enqueue(client, thread_id, "two")

    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"id", "threadId", "seq", "content", "createdAt"}
    uuid.UUID(body["id"])
    assert body["threadId"] == thread_id
    assert body["seq"] == 0
    assert body["content"] == {"text": "one"}
    assert isinstance(body["createdAt"], (int, float))

    listed = client.get(f"/api/threads/queue/get?thread_id={thread_id}")
    assert listed.status_code == 200
    rows = listed.json()
    assert [row["seq"] for row in rows] == [0, 1]
    assert [row["content"]["text"] for row in rows] == ["one", "two"]
    assert rows[1]["id"] == second.json()["id"]


def test_list_rejects_foreign_thread(client):
    admit_user(client, "aliceq@x.com")
    admit_user(client, "bobq@x.com")
    login(client, "aliceq@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "alice only"})["id"]
    assert _enqueue(client, thread_id, "kept").status_code == 200
    login(client, "bobq@x.com")

    assert _enqueue(client, thread_id, "stolen").status_code == 404
    assert client.get(f"/api/threads/queue/get?thread_id={thread_id}").status_code == 404


def test_update_and_delete_reject_foreign_row(client):
    admit_user(client, "aliceq2@x.com")
    admit_user(client, "bobq2@x.com")
    login(client, "aliceq2@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "alice only"})["id"]
    row_id = _enqueue(client, thread_id, "kept").json()["id"]
    login(client, "bobq2@x.com")

    updated = client.patch(
        f"/api/threads/queue/update/{row_id}", json={"content": {"text": "stolen"}}
    )
    assert updated.status_code == 404
    assert client.delete(f"/api/threads/queue/delete/{row_id}").status_code == 404

    login(client, "aliceq2@x.com")
    rows = client.get(f"/api/threads/queue/get?thread_id={thread_id}").json()
    assert [row["content"]["text"] for row in rows] == ["kept"]


def test_all_endpoints_need_a_session(client):
    no_id = "00000000-0000-0000-0000-000000000000"
    body = {"threadId": no_id, "content": {"text": "x"}}
    assert client.post("/api/threads/queue/create", json=body).status_code == 401
    assert client.get(f"/api/threads/queue/get?thread_id={no_id}").status_code == 401
    update = client.patch(f"/api/threads/queue/update/{no_id}", json={"content": {"text": "x"}})
    assert update.status_code == 401
    assert client.delete(f"/api/threads/queue/delete/{no_id}").status_code == 401


def test_eleventh_enqueue_answers_422(client):
    signin(client, "cap@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    filled = [_enqueue(client, thread_id, f"m{i}").status_code for i in range(10)]
    assert filled == [200] * 10

    resp = _enqueue(client, thread_id, "one too many")

    assert resp.status_code == 422
    rows = client.get(f"/api/threads/queue/get?thread_id={thread_id}").json()
    assert len(rows) == 10


def test_empty_text_answers_422(client):
    signin(client, "empty@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]

    assert _enqueue(client, thread_id, "").status_code == 422
    missing = client.post("/api/threads/queue/create", json={"threadId": thread_id, "content": {}})
    assert missing.status_code == 422


def test_update_changes_content_only(client):
    signin(client, "edit@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    original = _enqueue(client, thread_id, "draft").json()

    resp = client.patch(
        f"/api/threads/queue/update/{original['id']}",
        json={"content": {"text": "edited"}},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == original["id"]
    assert body["threadId"] == thread_id
    assert body["seq"] == original["seq"]
    assert body["createdAt"] == original["createdAt"]
    assert body["content"] == {"text": "edited"}


def test_delete_removes_the_row(client):
    signin(client, "del@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    kept = _enqueue(client, thread_id, "kept").json()
    gone = _enqueue(client, thread_id, "gone").json()

    resp = client.delete(f"/api/threads/queue/delete/{gone['id']}")

    assert resp.status_code == 204
    rows = client.get(f"/api/threads/queue/get?thread_id={thread_id}").json()
    assert [row["id"] for row in rows] == [kept["id"]]
    assert client.delete(f"/api/threads/queue/delete/{gone['id']}").status_code == 404


def test_deleting_the_thread_cascades_queue_rows(client, session_factory):
    signin(client, "cascade@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    _enqueue(client, thread_id, "one")
    _enqueue(client, thread_id, "two")

    assert client.delete(f"/api/threads/delete/{thread_id}").status_code == 204

    with session_factory() as db:
        count = db.scalar(
            select(func.count())
            .select_from(ChatQueuedMessage)
            .where(ChatQueuedMessage.thread_id == uuid.UUID(thread_id))
        )
    assert count == 0


def test_seq_keeps_incrementing_after_mid_queue_delete(client):
    signin(client, "seqs@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    _enqueue(client, thread_id, "a")
    middle = _enqueue(client, thread_id, "b").json()
    _enqueue(client, thread_id, "c")
    client.delete(f"/api/threads/queue/delete/{middle['id']}")

    added = _enqueue(client, thread_id, "d").json()

    assert added["seq"] == 3
    rows = client.get(f"/api/threads/queue/get?thread_id={thread_id}").json()
    assert [row["seq"] for row in rows] == [0, 2, 3]
    assert [row["content"]["text"] for row in rows] == ["a", "c", "d"]


def test_queue_rows_carry_the_session_tenant(client, session_factory):
    signin(client, "qtenant@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "scoped"})["id"]
    row_id = uuid.UUID(_enqueue(client, thread_id, "scoped").json()["id"])

    with session_factory() as db:
        row = db.scalar(select(ChatQueuedMessage).where(ChatQueuedMessage.id == row_id))
        link = db.scalar(select(UserTenant).where(UserTenant.user_id == row.user_id))

    assert row.tenant_id == link.tenant_id
    assert row.thread_id == uuid.UUID(thread_id)
