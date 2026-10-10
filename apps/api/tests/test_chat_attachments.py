"""Attachment resolution: binary parts -> model parts, caps, and markers.

Runs resolve_parts directly on a real session plus FakeObjectStore; the
HTTP wiring and share flattening live in test_chat_attachments_http.py.
"""

import base64
import io

import pytest
from api.authz import Principal
from api.chat import attachments, complete
from api.config import get_config
from api.files import service
from api.models import File, User
from crypto import tenant_scope
from storage import FakeObjectStore

BUCKET = get_config().storage.s3_bucket
VISION_FLAGS = {"vision": True, "pdf_input": True}
NO_FLAGS: dict = {}


def _pdf_bytes(text: str) -> bytes:
    """Smallest valid one-page PDF; pypdf needs a real xref table."""
    stream = f"BT /F1 24 Tf 100 700 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
            b" /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (i, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n" % (len(objs) + 1))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    )
    return out.getvalue()


PDF_BYTES = _pdf_bytes("Hello PDF")


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def store() -> FakeObjectStore:
    return FakeObjectStore()


def _user(db, email="user@x.com") -> User:
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.flush()
    return user


def _principal(user: User, tenant_id="t1") -> Principal:
    return Principal(user_id=user.id, email=user.email, tenant_id=tenant_id, roles=())


def _file(db, store, user, data, *, filename, content_type) -> File:
    return service.store_bytes(
        db,
        store,
        bucket=BUCKET,
        tenant_id="t1",
        user_id=user.id,
        purpose="attachment",
        filename=filename,
        content_type=content_type,
        data=data,
    )


def _binary(row: File, **overrides) -> dict:
    part = {
        "type": "binary",
        "id": str(row.id),
        "mimeType": row.content_type,
        "filename": row.filename,
    }
    part.update(overrides)
    return part


def _resolve(db, store, principal, parts, **flags) -> list:
    messages = [{"role": "user", "content": parts}]
    return attachments.resolve_parts(
        db, store, principal=principal, messages=messages, flags=flags
    )[0]["content"]


def test_image_becomes_image_url_under_vision(db, store):
    user = _user(db)
    row = _file(db, store, user, b"\x89PNG", filename="pic.png", content_type="image/png")
    parts = [{"type": "text", "text": "look"}, _binary(row)]

    resolved = _resolve(db, store, _principal(user), parts, vision=True)

    assert resolved[0] == parts[0]
    encoded = base64.b64encode(b"\x89PNG").decode()
    assert resolved[1] == {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{encoded}"},
    }


def test_image_without_vision_becomes_marker(db, store):
    user = _user(db)
    row = _file(db, store, user, b"\x89PNG", filename="pic.png", content_type="image/png")

    resolved = _resolve(db, store, _principal(user), [_binary(row)])

    assert resolved[0]["type"] == "text"
    assert "pic.png" in resolved[0]["text"]
    assert "not sent to the model" in resolved[0]["text"]


def test_pdf_becomes_file_part_under_pdf_input(db, store):
    user = _user(db)
    row = _file(db, store, user, PDF_BYTES, filename="doc.pdf", content_type="application/pdf")

    resolved = _resolve(db, store, _principal(user), [_binary(row)], pdf_input=True)

    encoded = base64.b64encode(PDF_BYTES).decode()
    assert resolved[0] == {
        "type": "file",
        "file": {
            "filename": "doc.pdf",
            "file_data": f"data:application/pdf;base64,{encoded}",
        },
    }


def test_pdf_extracts_text_without_pdf_input(db, store):
    user = _user(db)
    row = _file(db, store, user, PDF_BYTES, filename="doc.pdf", content_type="application/pdf")

    resolved = _resolve(db, store, _principal(user), [_binary(row)])

    assert resolved[0]["type"] == "text"
    assert "Attachment doc.pdf:" in resolved[0]["text"]
    assert "Hello PDF" in resolved[0]["text"]


def test_broken_pdf_falls_back_to_marker(db, store):
    user = _user(db)
    row = _file(db, store, user, b"not a pdf", filename="bad.pdf", content_type="application/pdf")

    resolved = _resolve(db, store, _principal(user), [_binary(row)])

    assert resolved[0]["type"] == "text"
    assert "bad.pdf" in resolved[0]["text"]
    assert "not sent to the model" in resolved[0]["text"]


def test_text_file_inlines_as_text(db, store):
    user = _user(db)
    row = _file(db, store, user, b"line one", filename="note.txt", content_type="text/plain")

    resolved = _resolve(db, store, _principal(user), [_binary(row)])

    assert resolved[0]["type"] == "text"
    assert "Attachment note.txt:" in resolved[0]["text"]
    assert "line one" in resolved[0]["text"]


def test_missing_file_id_becomes_marker(db, store):
    user = _user(db)
    part = {
        "type": "binary",
        "id": "00000000-0000-0000-0000-00000000dead",
        "mimeType": "image/png",
        "filename": "gone.png",
    }

    resolved = _resolve(db, store, _principal(user), [part], vision=True)

    assert resolved[0]["type"] == "text"
    assert "gone.png" in resolved[0]["text"]
    assert "not sent to the model" in resolved[0]["text"]


def test_binary_part_without_id_becomes_marker(db, store):
    user = _user(db)
    part = {"type": "binary", "mimeType": "image/png", "filename": "noid.png"}

    resolved = _resolve(db, store, _principal(user), [part], vision=True)

    assert resolved[0]["type"] == "text"
    assert "noid.png" in resolved[0]["text"]
    assert "not sent to the model" in resolved[0]["text"]


def test_unlisted_mime_becomes_marker(db, store):
    user = _user(db)
    data = b"zip-bytes"
    row = File(
        tenant_id="t1",
        scope="user",
        created_by_user_id=user.id,
        purpose="attachment",
        bucket=BUCKET,
        object_key="attachments/t1/zip-object",
        filename="pack.zip",
        content_type="application/zip",
        size_bytes=len(data),
        sha256="a" * 64,
    )
    with tenant_scope("t1"):
        db.add(row)
        db.flush()
    store.put(
        BUCKET, row.object_key, io.BytesIO(data), content_type="application/zip", size=len(data)
    )

    resolved = _resolve(db, store, _principal(user), [_binary(row)], **VISION_FLAGS)

    assert resolved[0]["type"] == "text"
    assert "pack.zip" in resolved[0]["text"]
    assert "not sent to the model" in resolved[0]["text"]


def test_resolved_bytes_over_cap_raises_cap_error(db, store, monkeypatch):
    # The spec pins 20 MiB; the monkeypatch only shrinks the accounting.
    assert attachments.MAX_RESOLVED_BYTES == 20 * 1024 * 1024
    monkeypatch.setattr(attachments, "MAX_RESOLVED_BYTES", 8)
    user = _user(db)
    row = _file(db, store, user, b"\x89PNG-nine", filename="pic.png", content_type="image/png")

    with pytest.raises(complete.MessageCapError):
        _resolve(db, store, _principal(user), [_binary(row)], vision=True)


def test_resolved_text_counts_toward_history_cap(db, store):
    user = _user(db)
    row = _file(db, store, user, b"x" * 200, filename="note.txt", content_type="text/plain")
    messages = [
        {"role": "user", "content": "y" * (complete.MAX_TOTAL_CHARS - 100)},
        {"role": "user", "content": [_binary(row)]},
    ]

    with pytest.raises(complete.MessageCapError):
        attachments.resolve_parts(
            db, store, principal=_principal(user), messages=messages, flags=NO_FLAGS
        )
