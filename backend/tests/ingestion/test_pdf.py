"""V1.0 PDF kabul kontrolleri. Fixture'lar kodda uretilir (ikili dosya yok)."""

import pytest
from pydantic import ValidationError

from documentflow.ingestion import PdfInspection, PdfRejectionReason, inspect_pdf
from tests.ingestion._pdf_builder import (
    corrupt_pdf,
    encrypted_pdf,
    image_only_pdf,
    text_layer_pdf,
)


def test_text_layer_pdf_is_accepted() -> None:
    result = inspect_pdf(text_layer_pdf())
    assert result.accepted is True
    assert result.reason is None
    assert result.page_count == 1
    assert result.text_character_count is not None
    assert result.text_character_count > 0


def test_extracted_text_reflects_document_content() -> None:
    short = inspect_pdf(text_layer_pdf("Fatura ABC2025000000123 Genel Toplam 3.600,00"))
    longer = inspect_pdf(
        text_layer_pdf("Fatura ABC2025000000123 Genel Toplam 3.600,00 Ara Toplam 3.000,00")
    )
    assert short.text_character_count is not None
    assert longer.text_character_count is not None
    assert longer.text_character_count > short.text_character_count


@pytest.mark.parametrize(
    "data",
    [b"", b"hello world", b"PDF-1.4 sahte", b"\x00\x01\x02", b"%PDF"],
)
def test_non_pdf_payload_is_rejected(data: bytes) -> None:
    result = inspect_pdf(data)
    assert result.accepted is False
    assert result.reason is PdfRejectionReason.not_pdf


def test_oversized_document_is_rejected_before_parsing() -> None:
    data = text_layer_pdf()
    result = inspect_pdf(data, max_bytes=len(data) - 1)
    assert result.reason is PdfRejectionReason.too_large
    # Boyut kontrolu ayristirmadan once gelir: sayfa bilgisi hesaplanmaz.
    assert result.page_count is None


def test_document_at_the_size_limit_is_accepted() -> None:
    data = text_layer_pdf()
    assert inspect_pdf(data, max_bytes=len(data)).accepted is True


def test_scanned_like_document_without_text_layer_is_rejected() -> None:
    result = inspect_pdf(image_only_pdf())
    assert result.reason is PdfRejectionReason.no_text_layer
    # Reddedilse bile gozlenen ozellikler raporlanir (teshis icin).
    assert result.page_count == 1
    assert result.text_character_count == 0


def test_text_threshold_is_configurable() -> None:
    data = text_layer_pdf("Kisa")
    assert inspect_pdf(data, min_text_characters=1).accepted is True
    assert inspect_pdf(data, min_text_characters=500).reason is PdfRejectionReason.no_text_layer


def test_encrypted_document_is_rejected() -> None:
    assert inspect_pdf(encrypted_pdf()).reason is PdfRejectionReason.encrypted


def test_corrupt_pdf_body_is_rejected_without_raising() -> None:
    assert inspect_pdf(corrupt_pdf()).reason is PdfRejectionReason.unreadable


def test_inspection_invariant_accepted_implies_no_reason() -> None:
    with pytest.raises(ValidationError):
        PdfInspection(accepted=True, reason=PdfRejectionReason.not_pdf)
    with pytest.raises(ValidationError):
        PdfInspection(accepted=False, reason=None)


def test_inspection_is_deterministic() -> None:
    data = text_layer_pdf()
    assert inspect_pdf(data) == inspect_pdf(data)
