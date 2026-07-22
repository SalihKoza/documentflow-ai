"""Icerik adresli belge saklama (dosya sistemi + metadata karari)."""

import hashlib
from pathlib import Path

import pytest

from documentflow.documents import StoredDocument, content_path, store_document

DATA = b"%PDF-1.4 sentetik fatura govdesi"


def test_document_is_written_under_the_root(tmp_path: Path) -> None:
    stored = store_document(DATA, root=tmp_path)
    target = tmp_path / stored.relative_path
    assert target.is_file()
    assert target.read_bytes() == DATA


def test_metadata_matches_the_content(tmp_path: Path) -> None:
    stored = store_document(DATA, root=tmp_path)
    assert stored.sha256 == hashlib.sha256(DATA).hexdigest()
    assert stored.size_bytes == len(DATA)


def test_path_is_content_addressed_and_sharded(tmp_path: Path) -> None:
    stored = store_document(DATA, root=tmp_path)
    assert stored.relative_path == content_path(stored.sha256)
    assert stored.relative_path.startswith(f"{stored.sha256[:2]}/")
    assert stored.relative_path.endswith(".pdf")


def test_storing_the_same_content_twice_keeps_one_file(tmp_path: Path) -> None:
    first = store_document(DATA, root=tmp_path)
    second = store_document(DATA, root=tmp_path)
    assert first == second
    assert len(list(tmp_path.rglob("*.pdf"))) == 1


def test_different_content_yields_different_paths(tmp_path: Path) -> None:
    first = store_document(DATA, root=tmp_path)
    second = store_document(DATA + b" farkli", root=tmp_path)
    assert first.relative_path != second.relative_path
    assert len(list(tmp_path.rglob("*.pdf"))) == 2


def test_no_temporary_file_is_left_behind(tmp_path: Path) -> None:
    store_document(DATA, root=tmp_path)
    assert list(tmp_path.rglob("*.tmp")) == []


def test_path_is_structurally_immune_to_traversal(tmp_path: Path) -> None:
    # Yol tamamen onaltilik hash'ten turer; disaridan gelen hicbir ad yola girmez.
    stored = store_document(DATA, root=tmp_path)
    assert ".." not in stored.relative_path
    resolved = (tmp_path / stored.relative_path).resolve()
    assert resolved.is_relative_to(tmp_path.resolve())


def test_stored_document_carries_no_document_bytes() -> None:
    fields = set(StoredDocument.model_fields)
    assert fields == {"sha256", "relative_path", "size_bytes"}


def test_shard_directory_is_created_on_demand(tmp_path: Path) -> None:
    stored = store_document(DATA, root=tmp_path)
    assert (tmp_path / stored.sha256[:2]).is_dir()


def test_missing_root_raises_rather_than_writing_elsewhere(tmp_path: Path) -> None:
    missing = tmp_path / "olmayan" / "kok"
    with pytest.raises(FileNotFoundError):
        store_document(DATA, root=missing)
    assert not missing.exists()
