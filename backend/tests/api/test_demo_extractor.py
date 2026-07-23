"""Yerleşik `recorded` demo yanıtının gerçekten çalıştığını kilitler.

Diğer API testleri `get_extractor`'ı override eder; bu yüzden uygulamanın
tarayıcıda GERÇEKTEN kullandığı yol (`deps.get_extractor` + yerleşik demo yanıtı)
onlar tarafından sürülmez. Demo JSON'u bozulursa suite yeşil kalır ve sorun ancak
tarayıcıda görünürdü — bu modül o boşluğu kapatır.

Veritabanı gerektirmez.
"""

import pytest

from documentflow.api.deps import get_extractor
from documentflow.core.config import Settings
from documentflow.extraction import ExtractionRequest, ExtractionStatus
from documentflow.flagging import build_review_flags
from documentflow.validation import validate_invoice


def _demo_settings() -> Settings:
    # Init argumani .env'den once gelir: yerel bir .env dosyasi testi etkilemez.
    return Settings(extraction_provider="recorded", recorded_response_path=None)


def test_builtin_demo_response_extracts_without_error() -> None:
    """Demo yanıtı üretim çevrim yolundan (`build_result`) sorunsuz geçer."""
    result = get_extractor(_demo_settings()).extract(
        ExtractionRequest(document_id="1", content=b"%PDF-")
    )

    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None
    assert result.parse_failures == ()
    # Gercek bir model cagrilmadigi kayitlarda da gorunur.
    assert result.metadata.provider == "recorded"
    assert result.metadata.model == "none"


def test_builtin_demo_response_produces_both_signal_severities() -> None:
    """Demo, review ekranının hem `review` hem `blocking` sinyalini göstermesini sağlar.

    Bilinçli iki sorun: `fatura_no` kâğıt fatura biçiminde (FNO-001) ve
    3.000,00 + 600,00 = 3.600,00 iken `genel_toplam` 3.599,00 (ARITH-001).
    """
    result = get_extractor(_demo_settings()).extract(
        ExtractionRequest(document_id="1", content=b"%PDF-")
    )
    assert result.invoice is not None

    flags = build_review_flags(result.invoice, validate_invoice(result.invoice))
    assert [flag.signal_code.value for flag in flags] == [
        "invoice_number_format",
        "header_arithmetic",
    ]
    assert [flag.severity.value for flag in flags] == ["review", "blocking"]


def test_unsupported_provider_fails_loudly() -> None:
    """Bilinmeyen sağlayıcı adı sessizce demo'ya düşmez."""
    with pytest.raises(ValueError, match="anthropic"):
        get_extractor(Settings(extraction_provider="anthropic"))
