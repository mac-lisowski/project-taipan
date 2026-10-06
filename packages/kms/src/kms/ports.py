"""Ports for key management backends.

Call sites depend on these protocols, so swapping the backend is a
new adapter, not a rewrite. Cipher lives in crypto.ports; this
re-export keeps one definition.
"""

from typing import Protocol

from crypto.ports import Cipher

__all__ = ["Cipher", "Provisioning"]


class Provisioning(Protocol):
    def create_project(self, name: str) -> str: ...

    def create_key(self, project_id: str, name: str) -> str: ...

    def delete_project(self, project_id: str) -> None: ...

    def rotate(self, key_id: str) -> int: ...
