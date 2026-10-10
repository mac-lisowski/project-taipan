"""Typed service errors; the router maps them to status codes."""

from __future__ import annotations


class PurposeNotAllowed(Exception):
    """The purpose is unknown or not open to browser uploads."""


class ScopeNotAllowed(Exception):
    """The scope is not one the purpose policy allows."""


class UnsupportedType(Exception):
    """The declared content type is not on the purpose allowlist."""


class TooLarge(Exception):
    """The upload exceeds the purpose size cap."""


class ObjectMissing(Exception):
    """The metadata row exists but the object bytes do not."""


class NotFound(Exception):
    """No visible file with this id for the principal."""


class InUse(Exception):
    """A consumer row (e.g. an artifact) still references this file."""
