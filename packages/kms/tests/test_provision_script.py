"""The provisioning script's operator contract, driven without a stack.

main() is imported from scripts/ and run with faked package calls and
monkeypatched env. Pins: the single stdout line, the found/created
stderr lines, the exit codes on every failure path, and stdout purity
when --verify fails after provisioning.
"""

import importlib.util
import pathlib
from types import ModuleType

import pytest
from kms import Ensured

SCRIPT = pathlib.Path(__file__).resolve().parents[3] / "scripts" / "provision_kms.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("provision_kms", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = load_script()
    monkeypatch.setenv("INFISICAL_ADMIN_TOKEN", "admin-token")
    return module


def fake_ensure(module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "ensure_project", lambda p, n: Ensured("proj-1", created=True))
    monkeypatch.setattr(module, "ensure_key", lambda p, t, n: Ensured("key-1", created=False))


def test_missing_admin_token_fails_before_any_output(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.delenv("INFISICAL_ADMIN_TOKEN")
    assert script.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "INFISICAL_ADMIN_TOKEN" in captured.err


def test_happy_path_prints_only_the_key_id_on_stdout(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    fake_ensure(script, monkeypatch)
    assert script.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == "key-1\n"
    assert "created project" in captured.err
    assert "found key" in captured.err


def test_created_vs_found_reaches_stderr(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(script, "ensure_project", lambda p, n: Ensured("proj-9", created=False))
    monkeypatch.setattr(script, "ensure_key", lambda p, t, n: Ensured("key-9", created=False))
    assert script.main([]) == 0
    assert "found project" in capsys.readouterr().err


def test_ensure_failure_keeps_stdout_clean(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from kms import KmsError

    def boom(p, n):
        raise KmsError("two kms projects named taipan-field-encryption")

    monkeypatch.setattr(script, "ensure_project", boom)
    assert script.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "taipan-field-encryption" in captured.err


def test_unexpected_errors_never_traceback(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def broken(p, n):
        raise KeyError("projects")

    monkeypatch.setattr(script, "ensure_project", broken)
    assert script.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unexpected error" in captured.err


def test_verify_without_runtime_token_fails_after_printing_the_id(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    fake_ensure(script, monkeypatch)
    monkeypatch.delenv("API_INFISICAL_TOKEN", raising=False)
    assert script.main(["--verify"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "key-1\n"
    assert "API_INFISICAL_TOKEN" in captured.err


def test_verify_hint_fails_with_the_id_still_on_stdout(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    fake_ensure(script, monkeypatch)
    monkeypatch.setenv("API_INFISICAL_TOKEN", "runtime-token")
    monkeypatch.setattr(script, "verify_key", lambda c, k: "grant hint text")
    monkeypatch.setattr(script, "InfisicalCipher", lambda url, token: object())
    assert script.main(["--verify"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "key-1\n"
    assert "grant hint text" in captured.err


def test_verify_ok_exits_zero(script: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    fake_ensure(script, monkeypatch)
    monkeypatch.setenv("API_INFISICAL_TOKEN", "runtime-token")
    monkeypatch.setattr(script, "verify_key", lambda c, k: None)
    monkeypatch.setattr(script, "InfisicalCipher", lambda url, token: object())
    assert script.main(["--verify"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "key-1\n"
    assert "verify ok" in captured.err
