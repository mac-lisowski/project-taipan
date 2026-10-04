"""Infisical smoke tests.

Skip when the instance is unreachable, same convention as the
Postgres tests. These cover what this repo adds - service wiring and
scripts/infisical-bootstrap.sh - not Infisical's own features.
"""

import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

INFISICAL_URL = os.environ.get("API_INFISICAL_URL", "http://localhost:8080")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{INFISICAL_URL}/api/status", timeout=2) as r:
            return r.status == 200
    except (OSError, urllib.error.URLError):
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="infisical not reachable")


def test_status_endpoint_ok():
    with urllib.request.urlopen(f"{INFISICAL_URL}/api/status", timeout=5) as r:
        assert r.status == 200


def _run_bootstrap() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "scripts/infisical-bootstrap.sh"],
        cwd=REPO_ROOT,
        env={**os.environ, "INFISICAL_URL": INFISICAL_URL},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def test_bootstrap_script_succeeds():
    res = _run_bootstrap()
    assert res.returncode == 0, res.stderr
    assert "bootstrap" in res.stdout


def test_bootstrap_script_is_idempotent():
    assert _run_bootstrap().returncode == 0
    res = _run_bootstrap()
    assert res.returncode == 0, res.stderr
    assert "already bootstrapped" in res.stdout
