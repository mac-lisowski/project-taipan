"""Idempotent provisioning: find first, create on miss.

KmsError from a finder propagates unwrapped: the adapter's
duplicate-project ambiguity error must reach the operator, so ensure
never retries and never swallows.
"""

from typing import NamedTuple

from kms.ports import Provisioning

__all__ = ["Ensured", "ensure_key", "ensure_project"]


class Ensured(NamedTuple):
    """The object's id, and whether this call had to create it."""

    id: str
    created: bool


def ensure_project(provisioning: Provisioning, name: str) -> Ensured:
    """Return the named project's id, creating it when absent."""
    project_id = provisioning.find_project(name)
    if project_id is None:
        return Ensured(provisioning.create_project(name), created=True)
    return Ensured(project_id, created=False)


def ensure_key(provisioning: Provisioning, project_id: str, name: str) -> Ensured:
    """Return the named key's id in the project, creating it when absent."""
    key_id = provisioning.find_key(project_id, name)
    if key_id is None:
        return Ensured(provisioning.create_key(project_id, name), created=True)
    return Ensured(key_id, created=False)
