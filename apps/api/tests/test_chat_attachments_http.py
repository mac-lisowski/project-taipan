"""Attachment resolution over HTTP: complete() wiring, verbatim history, shares."""

import base64

import httpx2
import pytest
from api.chat import attachments
from api.chat.gateway import get_gateway
from api.chat.models import get_model_catalog
from api.main import app
from api_testsupport import create_share, create_thread, model_catalog, signin
from storage import FakeObjectStore
from test_chat_attachments import PDF_BYTES
from test_chat_completion_http import FakeGateway

MISSING_ID = "00000000-0000-0000-0000-00000000dead"

_LISTING = {"data": [{"id": "vision-pro"}, {"id": "llama-3"}]}
_INFO = {
    "data": [
        {
            "model_name": "vision-pro",
            "model_info": {
                "mode": "chat",
                "supports_vision": True,
                "supports_pdf_input": True,
            },
        }
    ]
}


async def _catalog_handler(request):
    if request.url.path == "/model/info":
        return httpx2.Response(200, json=_INFO)
    return httpx2.Response(200, json=_LISTING)


@pytest.fixture
def wired(client):
    """Fake gateway plus a catalog where only vision-pro takes images/pdfs."""
    fake = FakeGateway()
    catalog = model_catalog(_catalog_handler, default="vision-pro")
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_model_catalog] = lambda: catalog
    yield fake
    app.dependency_overrides.pop(get_gateway, None)
    app.dependency_overrides.pop(get_model_catalog, None)


def _use_store(client) -> FakeObjectStore:
    fake = FakeObjectStore()
    client.app.state.object_store = fake
    return fake


def _upload(client, data, *, filename, content_type, scope="user") -> dict:
    resp = client.post(
        "/api/files",
        data={"purpose": "attachment", "scope": scope},
        files={"file": (filename, data, content_type)},
    )
    assert resp.status_code == 201
    return resp.json()


def _complete(client, thread_id, messages, **extra):
    return client.post(
        "/api/chat/complete",
        json={"threadId": thread_id, "runId": "r-1", "messages": messages, **extra},
    )


def test_thread_create_with_parts_derives_title_from_text(client):
    signin(client, "titled@x.com")
    parts = [
        {"type": "binary", "mimeType": "image/png", "id": MISSING_ID, "filename": "p.png"},
        {"type": "text", "text": "parts title"},
    ]

    body = create_thread(client, {"role": "user", "content": parts})

    assert body["title"] == "parts title"


def test_complete_resolves_for_gateway_but_stores_verbatim(client, wired):
    _use_store(client)
    signin(client, "attach@x.com")
    made = _upload(client, b"\x89PNG", filename="pic.png", content_type="image/png")
    thread_id = create_thread(client)["id"]
    parts = [
        {"type": "text", "text": "see this"},
        {
            "type": "binary",
            "mimeType": "image/png",
            "id": made["id"],
            "filename": "pic.png",
            "url": f"/api/files/{made['id']}/content",
        },
    ]

    resp = _complete(client, thread_id, [{"role": "user", "content": parts}], model="vision-pro")

    assert resp.status_code == 200
    sent = wired.calls[0][-1]
    assert sent["content"][0] == parts[0]
    assert sent["content"][1]["type"] == "image_url"
    assert sent["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    stored = client.get(f"/api/threads/get/{thread_id}").json()
    assert stored[0]["content"] == parts


def test_complete_marks_images_for_models_without_vision(client, wired):
    _use_store(client)
    signin(client, "novision@x.com")
    made = _upload(client, b"\x89PNG", filename="pic.png", content_type="image/png")
    thread_id = create_thread(client)["id"]
    parts = [
        {"type": "text", "text": "see this"},
        {"type": "binary", "mimeType": "image/png", "id": made["id"], "filename": "pic.png"},
    ]

    resp = _complete(client, thread_id, [{"role": "user", "content": parts}], model="llama-3")

    assert resp.status_code == 200
    sent = wired.calls[0][-1]
    assert sent["content"][1]["type"] == "text"
    assert "not sent to the model" in sent["content"][1]["text"]


def test_six_binary_parts_answers_422(client, wired):
    signin(client, "six@x.com")
    thread_id = create_thread(client)["id"]
    parts = [
        {
            "type": "binary",
            "mimeType": "image/png",
            "id": f"00000000-0000-0000-0000-0000000000{i:02d}",
            "filename": f"p{i}.png",
        }
        for i in range(6)
    ]

    resp = _complete(client, thread_id, [{"role": "user", "content": parts}])

    assert resp.status_code == 422


def test_resolved_bytes_over_cap_answers_422(client, wired, monkeypatch):
    # Shrink the cap so the route maps the resolver's MessageCapError to 422.
    monkeypatch.setattr(attachments, "MAX_RESOLVED_BYTES", 8)
    _use_store(client)
    signin(client, "bigattach@x.com")
    made = _upload(client, b"\x89PNG-nine", filename="pic.png", content_type="image/png")
    thread_id = create_thread(client)["id"]
    parts = [{"type": "binary", "mimeType": "image/png", "id": made["id"], "filename": "pic.png"}]

    resp = _complete(client, thread_id, [{"role": "user", "content": parts}], model="vision-pro")

    assert resp.status_code == 422
    assert wired.calls == []


def test_share_snapshot_flattens_parts_to_markdown(client):
    _use_store(client)
    signin(client, "flat@x.com")
    img = _upload(client, b"\x89PNG", filename="pic.png", content_type="image/png", scope="tenant")
    doc = _upload(
        client, PDF_BYTES, filename="doc.pdf", content_type="application/pdf", scope="tenant"
    )
    parts = [
        {"type": "text", "text": "files inside"},
        {"type": "binary", "mimeType": "image/png", "id": img["id"], "filename": "pic.png"},
        {"type": "binary", "mimeType": "application/pdf", "id": doc["id"], "filename": "doc.pdf"},
    ]
    thread = create_thread(client, {"role": "user", "content": parts})

    token = create_share(client, thread["id"])["token"]
    client.cookies.clear()
    body = client.get(f"/api/public/threads/{token}").json()

    content = body["messages"][0]["content"]
    assert isinstance(content, str)
    encoded = base64.b64encode(b"\x89PNG").decode()
    assert f"![](data:image/png;base64,{encoded})" in content
    assert "Attachment: doc.pdf" in content
    assert "files inside" in content


def test_share_snapshot_marks_attachment_when_object_gone(client):
    store = _use_store(client)
    signin(client, "goneflat@x.com")
    img = _upload(client, b"\x89PNG", filename="pic.png", content_type="image/png")
    parts = [{"type": "binary", "mimeType": "image/png", "id": img["id"], "filename": "pic.png"}]
    thread = create_thread(client, {"role": "user", "content": parts})
    store.clear()

    token = create_share(client, thread["id"])["token"]
    body = client.get(f"/api/public/threads/{token}").json()

    assert body["messages"][0]["content"] == "Attachment: pic.png"
