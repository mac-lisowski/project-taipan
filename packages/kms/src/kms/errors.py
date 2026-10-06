"""Typed error so call sites never inspect HTTP internals."""

from crypto.errors import CipherError


class KmsError(CipherError):
    """A KMS API call failed on the backend side."""
