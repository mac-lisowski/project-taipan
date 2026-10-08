"""Verify that a runtime token can actually use a provisioned key.

One encrypt-decrypt roundtrip with the caller's cipher. A 401 or 403
from the backend means the runtime identity lacks project membership,
so the hint names the role and the membership action. Any other
failure means the KMS did not answer as expected, so the hint points
at URL and backend health instead. Both hints never name the pinned
project; pinned names live only in the provisioning script.
"""

from crypto.errors import CipherError
from crypto.ports import Cipher

from kms.errors import KmsError

__all__ = ["BACKEND_HINT", "GRANT_HINT", "verify_key"]

GRANT_HINT = (
    "verify failed: the runtime token was rejected (401/403). "
    "Add its machine identity to the project membership with the "
    "built-in cryptographic-operator role (membership default is no-access)."
)

BACKEND_HINT = (
    "verify failed: the KMS did not answer as expected. "
    "Check API_INFISICAL_URL and backend health, then rerun. "
    "The key exists but this token could not roundtrip a payload."
)


def verify_key(cipher: Cipher, key_id: str) -> str | None:
    """Roundtrip a small payload; return the cause-matched hint on failure."""
    payload = b"taipan-verify"
    try:
        roundtripped = cipher.decrypt(key_id, cipher.encrypt(key_id, payload))
    except KmsError as exc:
        if exc.status_code in (401, 403):
            return GRANT_HINT
        return BACKEND_HINT
    except CipherError:
        # Transport-level failure: no HTTP status to branch on.
        return BACKEND_HINT
    if roundtripped != payload:
        # A backend that mangles payloads is not a grant problem.
        return BACKEND_HINT
    return None
