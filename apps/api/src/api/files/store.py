"""Object store composition root: build once, expose through ``app.state``.

Lives in the app, not the storage package: packages never import apps.
Mirrors ``api/mail.py`` (``build_email_sender`` + ``get_email_sender``).
"""

from __future__ import annotations

from fastapi import Request
from storage import ObjectStore, S3ObjectStore

from api.config import Config, get_config


def build_object_store(config: Config | None = None) -> ObjectStore:
    """Build the S3 adapter from server config. Construction never dials out."""
    cfg = config or get_config()
    return S3ObjectStore(
        cfg.storage.s3_endpoint,
        cfg.storage.s3_access_key,
        cfg.storage.s3_secret_key,
        region=cfg.storage.s3_region,
    )


def get_object_store(request: Request) -> ObjectStore:
    """Route dependency. App code receives the port only."""
    return request.app.state.object_store
