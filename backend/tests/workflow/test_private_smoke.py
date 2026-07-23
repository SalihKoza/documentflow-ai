r"""Lokal gerçek belgeyle private smoke test (varsayılan olarak atlanır).

Repoda gerçek fatura BULUNMAZ ve bulunmayacaktır (D-029). Bu test yalnızca
`DOCUMENTFLOW_PRIVATE_PDF` ortam değişkeni yerel bir PDF'e işaret ettiğinde
çalışır:

```powershell
$env:DOCUMENTFLOW_PRIVATE_PDF = "C:\...\data\private\freeze_candidates\originals\ornek.pdf"
uv run pytest tests/workflow/test_private_smoke.py
```

Belge yolu, adı ve içeriği hiçbir assert mesajına, log'a veya rapora yansımaz;
yalnızca yapısal özellikler (kabul edildi mi, kaç sayfa, zincir tamamlandı mı)
kontrol edilir.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from documentflow.extraction import ExtractionStatus, RecordedExtractor
from documentflow.ingestion import inspect_pdf
from documentflow.workflow import (
    apply_correction,
    approve,
    export_approved,
    ingest_document,
    run_extraction,
)
from tests.extraction._fixtures import wire_json, wire_payload

_ENV_VAR = "DOCUMENTFLOW_PRIVATE_PDF"


@pytest.fixture
def private_pdf() -> bytes:
    raw_path = os.environ.get(_ENV_VAR)
    if not raw_path:
        pytest.skip(f"{_ENV_VAR} tanimli degil; private smoke test atlandi")
    path = Path(raw_path)
    if not path.is_file():
        pytest.skip(f"{_ENV_VAR} bir dosyaya isaret etmiyor; private smoke test atlandi")
    return path.read_bytes()


def test_private_document_passes_the_v1_scope_gate(private_pdf: bytes) -> None:
    """Gerçek belge V1.0 kapsam kapısından geçiyor mu (metin katmanı var mı)."""
    inspection = inspect_pdf(private_pdf)
    # Hata mesajinda belge icerigi degil, yalnizca yapisal sonuc gorunur.
    assert inspection.accepted, f"belge V1.0 kapsaminda degil: {inspection.reason}"
    assert inspection.page_count is not None and inspection.page_count >= 1
    assert inspection.text_character_count is not None


def test_private_document_completes_the_whole_chain(
    session: Session, storage_root: Path, private_pdf: bytes
) -> None:
    """Yükle → çıkar → doğrula → düzelt → onayla → export zinciri gerçek bir PDF ile.

    Çıkarım hâlâ `recorded` sağlayıcıyla yapılır (model kararı ertelendi, D-049):
    bu test belgenin gerçekten çıkarıldığını DEĞİL, gerçek bir PDF'in ingestion,
    saklama ve iş akışı katmanlarından sorunsuz geçtiğini doğrular.
    """
    document = ingest_document(session, filename=None, data=private_pdf, storage_root=storage_root)
    assert document.accepted is True
    assert document.relative_path is not None
    assert (storage_root / document.relative_path).is_file()

    run = run_extraction(
        session,
        document,
        RecordedExtractor(wire_json(wire_payload())),
        storage_root=storage_root,
    )
    assert run.status == ExtractionStatus.ok.value

    apply_correction(session, run, "header.fatura_no", "ABC2025000000123")
    approve(session, run)
    record, body = export_approved(session, run)
    assert len(record.payload_sha256) == 64
    assert body
