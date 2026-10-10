"""Purpose policies: key prefix, mime allowlist, size cap, and scopes.

One policy per purpose. The service reads these to decide who may write
what, where the key lands, and how large the bytes may be.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

SCOPE_USER = "user"
SCOPE_TENANT = "tenant"


@dataclass(frozen=True)
class Policy:
    """The rules one purpose applies to every write under it."""

    prefix: str
    mime_patterns: tuple[str, ...]
    scopes: frozenset[str]
    browser_uploadable: bool
    # Scope for server-generated writes; a caller cannot pick a forbidden one.
    server_scope: str = SCOPE_USER
    # None defers to the configured upload cap.
    max_bytes: int | None = None


POLICIES: dict[str, Policy] = {
    "attachment": Policy(
        prefix="attachments/",
        mime_patterns=("image/*", "application/pdf", "text/plain"),
        scopes=frozenset({SCOPE_USER, SCOPE_TENANT}),
        browser_uploadable=True,
    ),
    # Service-only: no browser may mint an artifact through POST.
    "artifact": Policy(
        prefix="artifacts/",
        mime_patterns=("application/json",),
        scopes=frozenset({SCOPE_USER}),
        browser_uploadable=False,
    ),
}


def policy_for(purpose: str) -> Policy | None:
    """Return the policy for a purpose, or None when it is unknown."""
    return POLICIES.get(purpose)


def key_for(purpose: str, tenant_id: str, file_id: UUID) -> str:
    """Object key `{prefix}{tenant_id}/{file_id}`; opaque, filename stays in the row."""
    return f"{POLICIES[purpose].prefix}{tenant_id}/{file_id}"


def sanitize_filename(filename: str) -> str:
    """Drop any path and control bytes; never return an empty name."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(ch for ch in base if ch.isprintable()).strip().strip(".")
    return cleaned[:255] or "file"


def check_mime(policy: Policy, content_type: str) -> bool:
    """True when the declared type matches the policy allowlist."""
    mime = content_type.split(";", 1)[0].strip().lower()
    for pattern in policy.mime_patterns:
        if pattern.endswith("/*"):
            if mime.startswith(pattern[:-1]):
                return True
        elif mime == pattern:
            return True
    return False


def check_size(policy: Policy, size_bytes: int, *, cap: int) -> bool:
    """True when size_bytes fits the policy cap; `cap` fills a deferred policy."""
    limit = cap if policy.max_bytes is None else policy.max_bytes
    return size_bytes <= limit
