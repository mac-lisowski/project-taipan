"""Ports for key management backends.

Call sites depend on these protocols, so swapping the backend is a
new adapter, not a rewrite.
"""

from typing import Protocol


class Cipher(Protocol):
    def encrypt(self, key_id: str, data: bytes) -> str: ...

    def decrypt(self, key_id: str, ciphertext: str) -> bytes: ...


class Provisioning(Protocol):
    def create_project(self, name: str) -> str: ...

    def create_key(self, project_id: str, name: str) -> str: ...

    def delete_project(self, project_id: str) -> None: ...

    def rotate(self, key_id: str) -> int: ...
