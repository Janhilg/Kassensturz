import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOTS = [
    REPO_ROOT / "app.py",
    REPO_ROOT / "core",
    REPO_ROOT / "web",
]

COMPATIBILITY_IMPORTS = {
    "core.cash",
    "core.cash_service",
    "core.service",
    "core.storage",
    "core.storage_objects",
}

COMPATIBILITY_IMPORT_ALLOWLIST = {
    Path("app.py"): {"core.storage"},
    Path("core/cash/cash_service.py"): {"core.storage"},
    Path("core/export_utils.py"): {"core.storage"},
    Path("core/storage_objects/cash_storage.py"): {"core.storage"},
    Path("web/kassensturz_web_app.py"): {"core.storage"},
}


def _implementation_files() -> list[Path]:
    files = []
    for root in IMPLEMENTATION_ROOTS:
        if root.is_file():
            files.append(root)
        else:
            files.extend(root.rglob("*.py"))
    return sorted(files)


def _compatibility_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in COMPATIBILITY_IMPORTS:
                    imports.add(alias.name)
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        if node.module in COMPATIBILITY_IMPORTS:
            imports.add(node.module)
        elif node.module == "core":
            for alias in node.names:
                imported_module = f"core.{alias.name}"
                if imported_module in COMPATIBILITY_IMPORTS:
                    imports.add(imported_module)

    return imports


def test_implementation_files_do_not_add_compatibility_imports():
    violations = []

    for path in _implementation_files():
        relative_path = path.relative_to(REPO_ROOT)
        allowed_imports = COMPATIBILITY_IMPORT_ALLOWLIST.get(relative_path, set())
        disallowed_imports = _compatibility_imports(path) - allowed_imports
        if disallowed_imports:
            formatted_imports = ", ".join(sorted(disallowed_imports))
            violations.append(f"{relative_path}: {formatted_imports}")

    assert violations == []
