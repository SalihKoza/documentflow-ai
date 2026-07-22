"""Cekirdek katmanlarin FastAPI, veritabani ve LLM saglayicisindan bagimsizligi.

Bu, bir stil tercihi degil mimari bir kisittir (D-004): extraction, validation,
flagging, schema, parsing ve evaluation katmanlari transport ve saglayici
degistiginde degismemelidir. Import'lar AST ile taranir; calisma zamani davranisina
bagli degildir.
"""

import ast
from pathlib import Path

import pytest

import documentflow

# Cekirdek katmanlarda bulunmamasi gereken ust duzey paketler.
_FORBIDDEN_ROOTS = {
    "fastapi",
    "starlette",
    "uvicorn",
    "httpx",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "anthropic",
    "openai",
}

_PURE_PACKAGES = ("schema", "extraction", "validation", "flagging", "evaluation")


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _package_files(name: str) -> list[Path]:
    root = Path(documentflow.__file__).parent / name
    return sorted(root.glob("*.py"))


@pytest.mark.parametrize("package", _PURE_PACKAGES)
def test_core_package_has_no_framework_or_provider_imports(package: str) -> None:
    files = _package_files(package)
    assert files, f"{package} paketi bulunamadi"
    for path in files:
        offending = _imported_roots(path) & _FORBIDDEN_ROOTS
        assert not offending, f"{package}/{path.name} icinde yasak import: {sorted(offending)}"


def test_parsing_module_has_no_framework_or_provider_imports() -> None:
    path = Path(documentflow.__file__).parent / "parsing.py"
    assert not _imported_roots(path) & _FORBIDDEN_ROOTS


def test_ingestion_and_documents_stay_free_of_web_and_db_layers() -> None:
    # Bu iki katman dosya/PDF ile calisir; pypdf serbesttir, transport ve DB degil.
    for package in ("ingestion", "documents"):
        for path in _package_files(package):
            offending = _imported_roots(path) & _FORBIDDEN_ROOTS
            assert not offending, f"{package}/{path.name}: {sorted(offending)}"
