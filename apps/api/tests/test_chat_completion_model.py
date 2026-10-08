"""Per-request model: body field, catalog-checked 422, gateway pass-through."""

import httpx2
import pytest
from api.chat.gateway import get_gateway
from api.chat.models import get_model_catalog
from api.main import app
from api.schemas import CompletionIn
from api_testsupport import (
    CHAT_MODELS_LISTING,
    DEFAULT_CHAT_MODEL,
    create_thread,
    model_catalog,
    signin,
)
from test_chat_completion_http import CANNED_SSE, FakeGateway


async def _list_models(request):
    return httpx2.Response(200, json=CHAT_MODELS_LISTING)


@pytest.fixture
def wired(client):
    """Fake gateway plus the real catalog dep backed by a mocked listing."""
    fake = FakeGateway()
    catalog = model_catalog(_list_models)
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_model_catalog] = lambda: catalog
    yield fake
    app.dependency_overrides.pop(get_gateway, None)
    app.dependency_overrides.pop(get_model_catalog, None)


def _complete(client, thread_id, **extra):
    return client.post(
        "/api/chat/complete",
        json={
            "threadId": thread_id,
            "runId": "run-1",
            "messages": [{"role": "user", "content": "hi"}],
            **extra,
        },
    )


THREAD_ID = "00000000-0000-0000-0000-000000000001"


def test_completion_in_accepts_a_model_id():
    body = {"threadId": THREAD_ID, "runId": "run-1", "model": "llama-3"}

    payload = CompletionIn.model_validate(body)

    assert payload.model == "llama-3"


def test_completion_in_without_model_defaults_to_none():
    payload = CompletionIn(threadId=THREAD_ID, runId="run-1")

    assert payload.model is None


def test_unknown_model_answers_422_naming_the_served_set(client, wired):
    signin(client, "m422@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]
    # The detail must name the same ids the picker endpoint serves.
    served = [m["id"] for m in client.get("/api/chat/models").json()]
    assert served == [DEFAULT_CHAT_MODEL, "llama-3"]

    resp = _complete(client, thread_id, model="not-a-model")

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "not-a-model" in detail
    assert DEFAULT_CHAT_MODEL in detail
    assert "llama-3" in detail
    # A rejected id never opens the upstream stream.
    assert wired.calls == []


def test_listed_model_reaches_the_gateway_call(client, wired):
    signin(client, "mok@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]

    resp = _complete(client, thread_id, model="llama-3")

    assert resp.status_code == 200
    assert wired.models == ["llama-3"]


def test_absent_model_keeps_the_default_path(client, wired):
    signin(client, "mnone@x.com")
    thread_id = create_thread(client, {"role": "user", "content": "hi"})["id"]

    resp = _complete(client, thread_id)

    assert resp.status_code == 200
    assert resp.content == CANNED_SSE
    assert wired.models == [None]
