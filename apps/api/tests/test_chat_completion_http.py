"""Chat completion over HTTP: SSE passthrough, history rules, abort."""

import uuid
from types import SimpleNamespace

import pytest
from api import chat
from api.chat import gateway
from api.chat.gateway import GatewayError, get_gateway
from api.main import app
from api.models import User
from api_testsupport import admit_user, create_thread, create_user, login, signin
from crypto import tenant_scope

CANNED_SSE = (
    b'data: {"choices":[{"delta":{"content":"Ahoy"}}]}\n\n'
    b'data: {"choices":[{"delta":{"content":" captain"}}]}\n\n'
    b"data: [DONE]\n\n"
)
# Mid-event cuts prove the relay never reassembles or rewrites bytes.
CANNED_PARTS = [CANNED_SSE[:20], CANNED_SSE[20:60], CANNED_SSE[60:]]
CANNED_EVENTS = [
    CANNED_SSE[: CANNED_SSE.index(b"\n\n") + 2],
    CANNED_SSE[CANNED_SSE.index(b"\n\n") + 2 :],
]


class FakeGateway:
    """Canned byte stream in place of LiteLLM; records calls and closure."""

    def __init__(self, chunks: list[bytes] | None = None, error: Exception | None = None) -> None:
        self.chunks = CANNED_PARTS if chunks is None else chunks
        self.error = error
        self.calls: list[list[dict]] = []
        self.close_calls = 0

    def stream(self, messages: list[dict]):
        # Not async def: like the real gateway, the call only builds the
        # generator and does no work until the first iteration.
        self.calls.append(messages)
        return self._iter()

    async def _iter(self):
        try:
            for chunk in self.chunks:
                yield chunk
            if self.error is not None:
                raise self.error
        finally:
            self.close_calls += 1


@pytest.fixture
def fake_gateway(client):
    fake = FakeGateway()
    app.dependency_overrides[get_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_gateway, None)


def _complete(client, thread_id, *messages):
    return client.post(
        "/api/chat/complete",
        json={"threadId": thread_id, "runId": "run-1", "messages": list(messages)},
    )


def test_completion_streams_canned_bytes_unchanged(client, fake_gateway):
    signin(client, "streamer@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hello"})["id"]

    resp = _complete(client, thread_id, {"role": "user", "content": "hello"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.content == CANNED_SSE


def test_completion_prepends_system_prompt_to_gateway_messages(client, fake_gateway):
    signin(client, "prompted@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hello"})["id"]

    _complete(client, thread_id, {"role": "user", "content": "hello"})

    sent = fake_gateway.calls[0]
    assert sent[0]["role"] == "system"
    assert "component" in sent[0]["content"]
    assert sent[1:] == [{"role": "user", "content": "hello"}]


def test_completion_appends_assistant_row_after_stream_close(client, fake_gateway):
    signin(client, "closer@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hello"})["id"]

    _complete(client, thread_id, {"role": "user", "content": "hello"})

    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[-1] == {"role": "assistant", "content": "Ahoy captain"}


def test_completion_replaces_stored_history(client, fake_gateway):
    signin(client, "replacer@x.com")
    thread_id = create_thread(
        client,
        {"role": "user", "content": "old one"},
        {"role": "assistant", "content": "old reply"},
    )["id"]

    _complete(client, thread_id, {"role": "user", "content": "fresh start"})

    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored == [
        {"role": "user", "content": "fresh start"},
        {"role": "assistant", "content": "Ahoy captain"},
    ]


def test_completion_accepts_content_parts_and_stores_verbatim(client, fake_gateway):
    signin(client, "parts@x.com")
    thread_id = create_thread(client)["id"]
    parts = [{"type": "text", "text": "look at this"}]

    resp = _complete(client, thread_id, {"role": "user", "content": parts})

    assert resp.status_code == 200
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[0] == {"role": "user", "content": parts}


@pytest.mark.anyio
async def test_abort_stores_partial_text_and_cancels_upstream(client, session_factory):
    signin(client, "aborter@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "tell me a tale"})["id"]
    fake = FakeGateway(chunks=CANNED_EVENTS)
    incoming = [{"role": "user", "content": "tell me a tale"}]

    with session_factory() as db:
        user_id = db.query(User).filter_by(email="aborter@x.com").one().id
        thread = chat.threads.get(db, user_id, uuid.UUID(thread_id))
        # Outside HTTP the middleware cannot set the ambient scope, so the
        # run replays it the way the tenant guard expects during a request.
        with tenant_scope(thread.tenant_id):
            gen = chat.complete.stream_reply(
                db, thread, incoming, fake.stream(chat.complete.prepare(incoming))
            )
            await gen.__anext__()
            await gen.aclose()

        db.expire_all()
        rows = [row.content for row in thread.messages]

    assert fake.close_calls == 1
    assert rows == [
        {"role": "user", "content": "tell me a tale"},
        {"role": "assistant", "content": "Ahoy"},
    ]


def test_prestream_gateway_failure_answers_502_and_keeps_history(client, fake_gateway):
    signin(client, "failer@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "kept"})["id"]
    # No chunk precedes the error: the handshake itself dies.
    fake_gateway.chunks = []
    fake_gateway.error = GatewayError("gateway unavailable")

    resp = _complete(client, thread_id, {"role": "user", "content": "kept"})

    assert resp.status_code == 502
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored == [{"role": "user", "content": "kept"}]


def test_midstream_gateway_failure_emits_error_event_and_keeps_history(client, fake_gateway):
    signin(client, "midfailer@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "kept"})["id"]
    fake_gateway.chunks = list(CANNED_PARTS)
    fake_gateway.error = GatewayError("gateway died mid-stream")

    resp = _complete(client, thread_id, {"role": "user", "content": "kept"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert b'"error"' in resp.content
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored == [{"role": "user", "content": "kept"}]


def test_unconfigured_gateway_fails_fast_with_env_name(client, monkeypatch):
    signin(client, "unconfig@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    monkeypatch.setattr(
        gateway,
        "get_config",
        lambda: SimpleNamespace(chat=SimpleNamespace(litellm_api_key="")),
    )

    resp = _complete(client, thread_id, {"role": "user", "content": "hi"})

    assert resp.status_code == 500
    assert "API_LITELLM_API_KEY" in resp.json()["detail"]


def test_completion_requires_session(client):
    resp = client.post(
        "/api/chat/complete",
        json={
            "threadId": "00000000-0000-0000-0000-000000000000",
            "runId": "run-1",
            "messages": [],
        },
    )

    assert resp.status_code == 401


def test_foreign_thread_answers_404(client, fake_gateway):
    # Both users are admitted while the admin session is held.
    admit_user(client, "alice404@x.com")
    create_user(client, "bob404@x.com")
    login(client, "alice404@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "alice only"})["id"]
    login(client, "bob404@x.com")

    resp = _complete(client, thread_id, {"role": "user", "content": "stolen"})

    assert resp.status_code == 404


def test_oversized_history_answers_422(client, fake_gateway):
    signin(client, "big@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, {"role": "user", "content": "x" * 200_001})

    assert resp.status_code == 422


def test_too_many_messages_answers_422(client, fake_gateway):
    signin(client, "many@x.com")
    thread_id = create_thread(client)["id"]
    flood = [{"role": "user", "content": "x"} for _ in range(201)]

    resp = _complete(client, thread_id, *flood)

    assert resp.status_code == 422


def test_unknown_role_answers_422(client, fake_gateway):
    signin(client, "role@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, {"role": "tool", "content": "x"})

    assert resp.status_code == 422


def test_missing_run_id_answers_422(client, fake_gateway):
    signin(client, "runid@x.com")
    thread_id = create_thread(client)["id"]

    resp = client.post(
        "/api/chat/complete",
        json={"threadId": thread_id, "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 422
