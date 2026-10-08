#!/usr/bin/env python3
"""Provision the platform KMS key: one idempotent command.

Finds or creates the pinned project and key, then prints the key id
as the only stdout line. --verify proves the runtime token can use
the key. Human text goes to stderr; nothing is written to files.

Two identities, never mixed:
- INFISICAL_ADMIN_TOKEN provisions (find/create).
- API_INFISICAL_TOKEN is used only inside --verify.
"""

import argparse
import os
import sys

from kms import (
    Ensured,
    InfisicalCipher,
    InfisicalProvisioner,
    KmsError,
    ensure_key,
    ensure_project,
    verify_key,
)

# Same default as apps/api/src/api/config.py.
DEFAULT_INFISICAL_URL = "http://localhost:8080"
PROJECT_NAME = "taipan-field-encryption"
KEY_NAME = "platform-field-encryption"


def _fail(message: str) -> int:
    print(f"provision_kms: {message}", file=sys.stderr)
    return 1


def _announce(kind: str, name: str, ensured: Ensured) -> None:
    # The found/created difference matters: a "created" line when the
    # operator expected "found" exposes a duplicate or a blind token.
    verb = "created" if ensured.created else "found"
    print(f"provision_kms: {verb} {kind} {name} -> {ensured.id}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - an operator CLI never tracebacks
        return _fail(f"unexpected error: {type(exc).__name__}: {exc}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find or create the platform KMS project and key; print the key id."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="after provisioning, roundtrip the key with the runtime token",
    )
    return parser.parse_args(argv)


def _run(args: argparse.Namespace) -> int:
    # Fail loud before any API call: a missing admin token is a setup
    # gap, not a backend error.
    admin_token = os.environ.get("INFISICAL_ADMIN_TOKEN", "")
    if not admin_token:
        return _fail(
            "INFISICAL_ADMIN_TOKEN is not set; export the admin machine identity token first"
        )
    url = os.environ.get("API_INFISICAL_URL", DEFAULT_INFISICAL_URL)
    print(f"provision_kms: infisical at {url}", file=sys.stderr)

    provisioning = InfisicalProvisioner(url, admin_token)
    try:
        project = ensure_project(provisioning, PROJECT_NAME)
    except KmsError as exc:
        # Backend and ambiguity errors keep stdout clean and exit nonzero.
        return _fail(str(exc))
    _announce("project", PROJECT_NAME, project)
    try:
        key = ensure_key(provisioning, project.id, KEY_NAME)
    except KmsError as exc:
        return _fail(str(exc))
    _announce("key", KEY_NAME, key)
    print(key.id)

    if not args.verify:
        return 0
    runtime_token = os.environ.get("API_INFISICAL_TOKEN", "")
    if not runtime_token:
        return _fail("API_INFISICAL_TOKEN is not set; --verify needs the runtime token")
    hint = verify_key(InfisicalCipher(url, runtime_token), key.id)
    if hint is not None:
        return _fail(hint)
    print("provision_kms: verify ok, the runtime token can use the key", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
