"""Artifact downloads: GET /api/artifacts/{id}/download.

Documents stream as markdown attachments, tables as CSV. Seeding goes
through ``api.artifacts.service`` against the same FakeObjectStore the
route reads.
"""

import uuid

from api import artifacts
from api.authz import Principal
from api.config import get_config
from api.models import User, UserTenant
from api_testsupport import signin
from sqlalchemy import select
from storage import FakeObjectStore

BUCKET = get_config().storage.s3_bucket


def _seed(client, session_factory, email, *, title, type, content) -> str:
    with session_factory() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        tenant_id = db.scalar(select(UserTenant.tenant_id).where(UserTenant.user_id == user_id))
        principal = Principal(user_id=user_id, email=email, tenant_id=tenant_id, roles=())
        row = artifacts.create(
            db,
            client.app.state.object_store,
            bucket=BUCKET,
            principal=principal,
            type=type,
            title=title,
            content=content,
        )
        return str(row.id)


def test_document_download_streams_markdown_attachment(client, session_factory):
    signin(client, "dl@x.com")
    client.app.state.object_store = FakeObjectStore()
    aid = _seed(
        client,
        session_factory,
        "dl@x.com",
        title="Quarterly notes",
        type="taipan_document",
        content={"markdown": "# Report\n\nbody"},
    )

    resp = client.get(f"/api/artifacts/{aid}/download")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="quarterly-notes.md"' in disposition
    assert resp.text == "# Report\n\nbody"


def test_table_download_streams_csv_attachment(client, session_factory):
    signin(client, "dl2@x.com")
    client.app.state.object_store = FakeObjectStore()
    aid = _seed(
        client,
        session_factory,
        "dl2@x.com",
        title="people",
        type="taipan_table",
        content={"rows": [{"name": "ada", "age": 36}, {"name": "grace", "age": 85}]},
    )

    resp = client.get(f"/api/artifacts/{aid}/download")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'filename="people.csv"' in resp.headers["content-disposition"]
    assert resp.text.splitlines() == ["name,age", "ada,36", "grace,85"]


def test_download_unknown_artifact_is_404(client):
    signin(client, "dl3@x.com")
    client.app.state.object_store = FakeObjectStore()

    assert client.get(f"/api/artifacts/{uuid.uuid4()}/download").status_code == 404
