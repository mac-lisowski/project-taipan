"""Chat threads over HTTP: the five storage endpoints, owner scoped."""

import uuid

from api.models import ChatMessage, ChatThread, UserTenant
from api_testsupport import admit_user, create_thread, login, signin
from sqlalchemy import func, select


def test_create_returns_thread_shape_and_persists_messages(client):
    signin(client, "creator@x.com")

    body = create_thread(
        client,
        {"role": "user", "content": "Hello captain"},
        {"role": "assistant", "content": "Ahoy"},
    )

    assert set(body) == {"id", "title", "createdAt"}
    uuid.UUID(body["id"])
    assert body["title"] == "Hello captain"
    assert isinstance(body["createdAt"], (int, float))
    stored = client.get(f"/api/threads/get/{body['id']}")
    assert stored.status_code == 200
    assert stored.json() == [
        {"role": "user", "content": "Hello captain"},
        {"role": "assistant", "content": "Ahoy"},
    ]


def test_title_caps_long_first_message(client):
    signin(client, "longtitle@x.com")

    body = create_thread(client, {"role": "user", "content": "x" * 300})

    assert body["title"] == "x" * 100


def test_title_falls_back_without_user_message(client):
    signin(client, "notitle@x.com")

    body = create_thread(client, {"role": "assistant", "content": "hi"})

    assert body["title"] == "New chat"


def test_unknown_message_role_is_rejected(client):
    signin(client, "roles@x.com")

    resp = client.post("/api/threads/create", json={"messages": [{"role": "tool", "content": "x"}]})

    assert resp.status_code == 422


def test_list_orders_newest_first_and_pages_without_duplicates(client):
    signin(client, "lister@x.com")
    made = [create_thread(client, {"role": "user", "content": f"t{i}"})["id"] for i in range(23)]

    page1 = client.get("/api/threads/get")
    body1 = page1.json()
    ids1 = [t["id"] for t in body1["threads"]]

    assert page1.status_code == 200
    assert len(ids1) == 20
    assert ids1 == made[:2:-1]
    assert "nextCursor" in body1
    cursor = body1["nextCursor"]
    page2 = client.get(f"/api/threads/get?cursor={cursor}")
    body2 = page2.json()
    ids2 = [t["id"] for t in body2["threads"]]
    assert ids2 == made[2::-1]
    assert set(ids1).isdisjoint(ids2)
    assert "nextCursor" not in body2


def test_broken_cursor_answers_400(client):
    signin(client, "cursor@x.com")

    resp = client.get("/api/threads/get?cursor=garbage")

    assert resp.status_code == 400


def test_get_messages_returns_stored_order(client):
    signin(client, "reader@x.com")
    body = create_thread(
        client,
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
    )

    resp = client.get(f"/api/threads/get/{body['id']}")

    assert [m["content"] for m in resp.json()] == ["one", "two", "three"]


def test_update_renames_and_round_trips_created_at(client):
    signin(client, "renamer@x.com")
    body = create_thread(client, {"role": "user", "content": "draft"})

    resp = client.patch(
        f"/api/threads/update/{body['id']}",
        json={"id": body["id"], "title": "Renamed", "createdAt": body["createdAt"]},
    )

    assert resp.status_code == 200
    renamed = resp.json()
    assert renamed["id"] == body["id"]
    assert renamed["title"] == "Renamed"
    assert renamed["createdAt"] == body["createdAt"]


def test_delete_returns_204_and_removes_messages(client, session_factory):
    signin(client, "deleter@x.com")
    body = create_thread(client, {"role": "user", "content": "gone soon"})

    resp = client.delete(f"/api/threads/delete/{body['id']}")

    assert resp.status_code == 204
    assert client.get(f"/api/threads/get/{body['id']}").status_code == 404
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ChatThread)) == 0
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0


def test_all_endpoints_need_a_session(client):
    no_thread = "00000000-0000-0000-0000-000000000000"
    assert client.get("/api/threads/get").status_code == 401
    assert client.post("/api/threads/create", json={"messages": []}).status_code == 401
    assert client.get(f"/api/threads/get/{no_thread}").status_code == 401
    update = client.patch(f"/api/threads/update/{no_thread}", json={"title": "x"})
    assert update.status_code == 401
    assert client.delete(f"/api/threads/delete/{no_thread}").status_code == 401


def test_user_b_cannot_touch_user_a_thread(client):
    admit_user(client, "alice@x.com")
    admit_user(client, "bob@x.com")
    login(client, "alice@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "alice only"})["id"]
    login(client, "bob@x.com")

    assert client.get("/api/threads/get").json()["threads"] == []
    assert client.get(f"/api/threads/get/{thread_id}").status_code == 404
    renamed = client.patch(
        f"/api/threads/update/{thread_id}", json={"title": "stolen", "createdAt": 0}
    )
    assert renamed.status_code == 404
    assert client.delete(f"/api/threads/delete/{thread_id}").status_code == 404


def test_thread_rows_carry_the_session_tenant(client, session_factory):
    signin(client, "tenanted@x.com")
    body = create_thread(client, {"role": "user", "content": "scoped"})

    with session_factory() as db:
        row = db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(body["id"])))
        link = db.scalar(select(UserTenant).where(UserTenant.user_id == row.user_id))

    assert row.tenant_id == link.tenant_id
