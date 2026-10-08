"""Shared live-stack helpers for the kms suite.

Skip-when-down convention: live tests carry the `live_only` mark and
skip when Infisical is unreachable or the token is unset. A real
module, not conftest, so any collection order can import it.
"""

import os
import urllib.error
import urllib.request

import pytest

INFISICAL_URL = os.environ.get("API_INFISICAL_URL", "http://localhost:8080")
TOKEN = os.environ.get("API_INFISICAL_TOKEN", "")


def _reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{INFISICAL_URL}/api/status", timeout=2) as r:
            return r.status == 200
    except (OSError, urllib.error.URLError):
        return False


live_only = pytest.mark.skipif(
    not _reachable() or not TOKEN, reason="infisical not reachable or token unset"
)
