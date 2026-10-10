"""save_artifact tool calls: advert gated on flags, fragments to artifacts.

Each test wires a recording FakeGateway plus a catalog where tools-pro
carries function_calling+tool_choice, no-choice carries only
function_calling, and plain carries neither. The FakeObjectStore on
app.state catches artifact bytes the persist path writes at stream close.
"""

import json
from types import SimpleNamespace

import httpx2
import pytest
from api.chat.gateway import get_gateway
from api.chat.models import get_model_catalog
from api.main import app
from api_testsupport import create_thread, model_catalog, signin
from storage import FakeObjectStore
from test_chat_completion_http import FakeGateway


def _sse(event: dict) -> bytes:
    return b"data: " + json.dumps(event).encode() + b"\n\n"


def _tool_delta(index: int, **fragment) -> dict:
    return {"choices": [{"delta": {"tool_calls": [{"index": index, **fragment}]}}]}


def _text_delta(text: str) -> dict:
    return {"choices": [{"delta": {"content": text}}]}


def _open_call(index: int, call_id: str) -> dict:
    return _tool_delta(
        index,
        id=call_id,
        type="function",
        function={"name": "save_artifact", "arguments": ""},
    )


def _arg_fragment(index: int, text: str) -> dict:
    return _tool_delta(index, function={"arguments": text})


_DOC_ARGS = json.dumps(
    {"title": "Q3 report", "type": "taipan_document", "content": "# Report\n\nbody"}
)
# The arguments string splits mid-key across two deltas.
_DOC_SSE = (
    _sse(_open_call(0, "call_doc"))
    + _sse(_arg_fragment(0, _DOC_ARGS[:25]))
    + _sse(_arg_fragment(0, _DOC_ARGS[25:]))
    + _sse(_text_delta("Saved it."))
    + b"data: [DONE]\n\n"
)

_ROWS_ARGS = json.dumps(
    {"title": "Scores", "type": "taipan_table", "content": [{"q": 1}, {"q": 2}]}
)
_ROWS_SSE = (
    _sse(_open_call(0, "call_rows")) + _sse(_arg_fragment(0, _ROWS_ARGS)) + b"data: [DONE]\n\n"
)

_BAD_SSE = (
    _sse(_open_call(0, "call_bad"))
    + _sse(_arg_fragment(0, "{not json"))
    + _sse(_text_delta("done"))
    + b"data: [DONE]\n\n"
)

_LISTING = {"data": [{"id": "tools-pro"}, {"id": "no-choice"}, {"id": "plain"}]}
_INFO = {
    "data": [
        {
            "model_name": "tools-pro",
            "model_info": {
                "mode": "chat",
                "supports_function_calling": True,
                "supports_tool_choice": True,
            },
        },
        {
            "model_name": "no-choice",
            "model_info": {"mode": "chat", "supports_function_calling": True},
        },
    ]
}


async def _catalog_handler(request):
    if request.url.path == "/model/info":
        return httpx2.Response(200, json=_INFO)
    return httpx2.Response(200, json=_LISTING)


@pytest.fixture
def wired(client):
    fake = FakeGateway(chunks=[_DOC_SSE])
    store = FakeObjectStore()
    client.app.state.object_store = store
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_model_catalog] = lambda: model_catalog(
        _catalog_handler, default="tools-pro"
    )
    yield SimpleNamespace(gateway=fake, store=store)
    app.dependency_overrides.pop(get_gateway, None)
    app.dependency_overrides.pop(get_model_catalog, None)


def _complete(client, thread_id, **extra):
    return client.post(
        "/api/chat/complete",
        json={
            "threadId": thread_id,
            "runId": "r-1",
            "messages": [{"role": "user", "content": "save me a report"}],
            **extra,
        },
    )


def _artifacts(client) -> list[dict]:
    resp = client.get("/api/artifacts")
    assert resp.status_code == 200
    return resp.json()["artifacts"]


def test_sse_bytes_relay_unchanged_with_tool_calls(client, wired):
    signin(client, "relay@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, model="tools-pro")

    assert resp.status_code == 200
    assert resp.content == _DOC_SSE


def test_tool_call_fragments_upsert_one_artifact(client, wired):
    signin(client, "doc@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, model="tools-pro")

    assert resp.status_code == 200
    rows = _artifacts(client)
    assert len(rows) == 1
    assert (rows[0]["title"], rows[0]["type"]) == ("Q3 report", "taipan_document")
    assert rows[0]["threadId"] == thread_id
    body = client.get(f"/api/artifacts/{rows[0]['id']}").json()
    assert body["content"] == {"markdown": "# Report\n\nbody"}
    assert len(wired.store.list_objects()) == 1


def test_tool_calls_persist_on_the_assistant_message(client, wired):
    signin(client, "replay@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="tools-pro")

    stored = client.get(f"/api/threads/get/{thread_id}").json()
    last = stored[-1]
    assert last["role"] == "assistant"
    assert last["content"] == "Saved it."
    assert last["tool_calls"] == [
        {
            "id": "call_doc",
            "type": "function",
            "function": {"name": "save_artifact", "arguments": _DOC_ARGS},
        }
    ]


def test_table_call_stores_a_rows_body(client, wired):
    wired.gateway.chunks = [_ROWS_SSE]
    signin(client, "table@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="tools-pro")

    rows = _artifacts(client)
    assert len(rows) == 1
    assert rows[0]["type"] == "taipan_table"
    body = client.get(f"/api/artifacts/{rows[0]['id']}").json()
    assert body["content"] == {"rows": [{"q": 1}, {"q": 2}]}


def test_two_tool_calls_create_two_artifacts(client, wired):
    a_args = json.dumps({"title": "alpha", "type": "taipan_document", "content": "a"})
    b_args = json.dumps({"title": "beta", "type": "taipan_document", "content": "b"})
    wired.gateway.chunks = [
        _sse(_open_call(0, "call_a"))
        + _sse(_open_call(1, "call_b"))
        + _sse(_arg_fragment(1, b_args))
        + _sse(_arg_fragment(0, a_args))
        + b"data: [DONE]\n\n"
    ]
    signin(client, "pair@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="tools-pro")

    assert sorted(row["title"] for row in _artifacts(client)) == ["alpha", "beta"]
    assert len(wired.store.list_objects()) == 2


def test_malformed_arguments_skip_the_artifact_not_the_stream(client, wired):
    wired.gateway.chunks = [_BAD_SSE]
    signin(client, "bad@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, model="tools-pro")

    assert resp.status_code == 200
    assert resp.content == _BAD_SSE
    assert _artifacts(client) == []
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[-1]["tool_calls"][0]["function"]["arguments"] == "{not json"


def test_wrong_content_shape_skips_the_artifact(client, wired):
    args = json.dumps({"title": "odd", "type": "taipan_document", "content": 42})
    wired.gateway.chunks = [
        _sse(_open_call(0, "call_odd")) + _sse(_arg_fragment(0, args)) + b"data: [DONE]\n\n"
    ]
    signin(client, "odd@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, model="tools-pro")

    assert resp.status_code == 200
    assert _artifacts(client) == []


class _BoomStore(FakeObjectStore):
    """Every put fails: an S3 outage mid-persist must not kill the reply."""

    def put(self, *args, **kwargs):
        raise RuntimeError("s3 down")


def test_upsert_failure_still_persists_the_reply(client, wired):
    client.app.state.object_store = _BoomStore()
    signin(client, "outage@x.com")
    thread_id = create_thread(client)["id"]

    resp = _complete(client, thread_id, model="tools-pro")

    assert resp.status_code == 200
    assert _artifacts(client) == []
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[-1]["content"] == "Saved it."
    assert stored[-1]["tool_calls"][0]["id"] == "call_doc"


def test_tools_and_tool_choice_sent_when_both_flags_set(client, wired):
    signin(client, "full@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="tools-pro")

    tools = wired.gateway.tools[-1]
    assert [t["function"]["name"] for t in tools] == ["save_artifact"]
    assert wired.gateway.tool_choices[-1] == "auto"


def test_tool_choice_omitted_without_its_flag(client, wired):
    signin(client, "nochoice@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="no-choice")

    assert [t["function"]["name"] for t in wired.gateway.tools[-1]] == ["save_artifact"]
    assert wired.gateway.tool_choices[-1] is None


def test_no_tools_upstream_without_function_calling(client, wired):
    signin(client, "plain@x.com")
    thread_id = create_thread(client)["id"]

    _complete(client, thread_id, model="plain")

    assert wired.gateway.tools[-1] is None
    assert wired.gateway.tool_choices[-1] is None
    assert _artifacts(client) == []
