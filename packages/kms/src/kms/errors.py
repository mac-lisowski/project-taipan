"""Typed error so call sites never inspect HTTP internals."""

from crypto.errors import CipherError


class KmsError(CipherError):
    """A KMS API call failed on the backend side.

    status_code carries the HTTP status when the backend answered;
    transport-level failures leave it None. Call sites branch on it
    instead of parsing messages.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
