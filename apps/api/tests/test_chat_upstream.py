"""Upstream hygiene: stored tool_calls never reach the gateway, partial
replies persist on mid-stream failure."""

import httpx2
import pytest
from api.chat.gateway import GatewayError, get_gateway
from api.chat.models import get_model_catalog
from api.main import app
from api_testsupport import create_thread, model_catalog, signin
from storage import FakeObjectStore
from test_chat_completion_http import FakeGateway
from test_chat_tools import _INFO, _LISTING, _sse, _text_delta


async def _catalog_handler(request):
    if request.url.path == "/model/info":
        return httpx2.Response(200, json=_INFO)
    return httpx2.Response(200, json=_LISTING)


@pytest.fixture
def wired(client):
    fake = FakeGateway(chunks=[_sse(_text_delta("ok.")) + b"data: [DONE]\n\n"])
    client.app.state.object_store = FakeObjectStore()
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_model_catalog] = lambda: model_catalog(
        _catalog_handler, default="tools-pro"
    )
    yield fake
    app.dependency_overrides.pop(get_gateway, None)
    app.dependency_overrides.pop(get_model_catalog, None)


def _complete(client, thread_id, messages):
    return client.post(
        "/api/chat/complete",
        json={"threadId": thread_id, "runId": "r-1", "messages": messages},
    )


def test_replayed_tool_calls_stay_out_of_upstream(client, wired):
    signin(client, "replay@x.com")
    thread_id = create_thread(client)["id"]
    messages = [
        {"role": "user", "content": "make a report"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "save_artifact", "arguments": "{}"},
                }
            ],
        },
        {"role": "user", "content": "thanks"},
    ]

    resp = _complete(client, thread_id, messages)

    assert resp.status_code == 200
    sent = wired.calls[-1]
    assert all("tool_calls" not in message for message in sent)
    assert all(message["role"] != "tool" for message in sent)
    assistant = [m for m in sent if m.get("role") == "assistant"]
    assert assistant and assistant[0]["content"] == ""
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[1]["tool_calls"][0]["id"] == "call_1"


def test_mid_stream_gateway_error_persists_partial_reply(client, wired):
    signin(client, "flake@x.com")
    thread_id = create_thread(client)["id"]
    partial = _sse(_text_delta("half of a"))
    wired.chunks = [partial]
    wired.error = GatewayError("upstream reset")

    resp = _complete(client, thread_id, [{"role": "user", "content": "hi"}])

    assert resp.status_code == 200
    assert b'"type": "gateway_error"' in resp.content
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[-1]["role"] == "assistant"
    assert stored[-1]["content"] == "half of a"
