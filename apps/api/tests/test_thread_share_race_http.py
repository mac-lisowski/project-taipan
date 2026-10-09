"""Concurrent share create: the loser must recover to the winner's row."""

from api.chat import shares
from api.models import ChatThreadShare
from api_testsupport import create_share, create_thread, signin
from sqlalchemy import func, select


def test_create_recovers_when_a_concurrent_insert_wins(client, session_factory, monkeypatch):
    signin(client, "racer@x.com")
    thread = create_thread(client, {"role": "user", "content": "x"})
    winner = create_share(client, thread["id"])
    # The first lookup misses, as if the winner committed between the
    # select and the insert; ON CONFLICT must absorb the loser and the
    # re-select must return the winner.
    real_lookup = shares._unrevoked_share
    missed = []

    def blind_first_call(session, thread_id):
        if not missed:
            missed.append(thread_id)
            return None
        return real_lookup(session, thread_id)

    monkeypatch.setattr(shares, "_unrevoked_share", blind_first_call)

    repeat = create_share(client, thread["id"])

    assert repeat["token"] == winner["token"]
    assert client.get(f"/api/public/threads/{repeat['token']}").status_code == 200
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ChatThreadShare)) == 1
