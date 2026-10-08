"""Mail call-site wiring: one app name home, all mail call sites route through link mail.

Scans the api source files on disk with the ast module. A runtime
vars() scan would let an unimported module escape the check.
"""

import ast
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "src" / "api"

APP_NAME_LITERAL = "Taipan"
APP_NAME_HOME = "mail.py"

# The three modules that mail links or notices per the mailer spec.
CALL_SITES = (
    "registration/service.py",
    "password_reset/service.py",
    "password_change/notice.py",
)

# Direct seam calls in a call site skip the module's link build and guard.
BYPASS_CALLED_NAMES = {"rendered_send", "send"}


def _api_sources() -> list[Path]:
    files = sorted(API_SRC.rglob("*.py"))
    # The scan must not be vacuous: the real tree holds the call sites.
    assert files, f"no api sources found under {API_SRC}"
    for rel in CALL_SITES:
        assert (API_SRC / rel).is_file(), f"call site missing from the scan: {rel}"
    return files


def _assigned_string_values(tree: ast.AST) -> list[str]:
    """Values bound by plain assignments; usages and mail copy stay out."""
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values.append(node.value.value)
    return values


def _imported_modules(tree: ast.AST) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _called_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            if isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def _string_constants(tree: ast.AST) -> list[str]:
    """Every string literal in the module, including f-string chunks."""
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
    return values


def _hand_built_link_pieces(tree: ast.AST) -> list[str]:
    """URL fragments a call site must never hold; link building lives in link_mail."""
    return [v for v in _string_constants(tree) if v.startswith("http") or "?" in v]


def test_app_name_literal_is_assigned_exactly_once_across_api_sources():
    homes = []
    for path in _api_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if APP_NAME_LITERAL in _assigned_string_values(tree):
            homes.append(str(path.relative_to(API_SRC)))

    # One home means a rename or mail policy change touches one file.
    assert homes == [APP_NAME_HOME]


def test_each_mail_call_site_routes_through_link_mail():
    scanned = []
    failures = []
    for rel in CALL_SITES:
        scanned.append(rel)
        tree = ast.parse((API_SRC / rel).read_text(encoding="utf-8"), filename=rel)
        if "api.link_mail" not in _imported_modules(tree):
            failures.append(f"{rel} does not import the link mail module")
        bypasses = sorted(_called_names(tree) & BYPASS_CALLED_NAMES)
        if bypasses:
            failures.append(f"{rel} bypasses the link mail module, calls {bypasses}")
        pieces = _hand_built_link_pieces(tree)
        if pieces:
            failures.append(f"{rel} hand-builds a link, found {pieces}")

    # The scan must not be vacuous: every named call site was parsed and checked.
    assert scanned == list(CALL_SITES)
    assert failures == []
