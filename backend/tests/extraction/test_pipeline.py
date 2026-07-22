"""Uctan uca zincir: ingestion -> recorded extraction -> validation -> flagging.

Gercek bir fatura PDF'i repoda bulunmadigindan zincir sentetik bir metin katmanli
PDF ve kaydedilmis bir sagalayici yaniti ile surulur. Ag erisimi ve API anahtari
gerekmez.
"""

from decimal import Decimal

from documentflow.extraction import ExtractionRequest, ExtractionStatus, RecordedExtractor
from documentflow.flagging import FlagSeverity, FlagSignal, build_review_flags
from documentflow.ingestion import inspect_pdf
from documentflow.validation import validate_invoice
from tests.extraction._fixtures import ok_field, wire_json, wire_payload
from tests.ingestion._pdf_builder import image_only_pdf, text_layer_pdf


def _request() -> ExtractionRequest:
    data = text_layer_pdf()
    inspection = inspect_pdf(data)
    assert inspection.accepted is True
    return ExtractionRequest(
        document_id="FZ-SENTETIK-001",
        content=data,
        page_count=inspection.page_count,
    )


def test_clean_document_flows_through_without_flags() -> None:
    result = RecordedExtractor(wire_json(wire_payload())).extract(_request())
    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None

    report = validate_invoice(result.invoice)
    assert report.findings == ()
    assert report.review_required is False

    flags = build_review_flags(result.invoice, report, parse_failures=result.parse_failures)
    assert flags == ()


def test_arithmetic_error_reaches_a_blocking_flag() -> None:
    payload = wire_payload()
    payload["header"]["genel_toplam"] = ok_field("3.599,00")
    result = RecordedExtractor(wire_json(payload)).extract(_request())
    assert result.invoice is not None
    assert result.invoice.header.genel_toplam.value == Decimal("3599.00")

    report = validate_invoice(result.invoice)
    flags = build_review_flags(result.invoice, report, parse_failures=result.parse_failures)

    assert [flag.signal_code for flag in flags] == [FlagSignal.header_arithmetic]
    assert flags[0].severity is FlagSeverity.blocking
    assert flags[0].originating_rule == "ARITH-001"


def test_parse_failure_survives_the_whole_chain() -> None:
    payload = wire_payload()
    payload["header"]["ara_toplam"] = ok_field("uc bin lira")
    result = RecordedExtractor(wire_json(payload)).extract(_request())
    assert result.parse_failures == ("header.ara_toplam",)
    assert result.invoice is not None

    report = validate_invoice(result.invoice)
    flags = build_review_flags(result.invoice, report, parse_failures=result.parse_failures)

    assert [flag.signal_code for flag in flags] == [FlagSignal.parse_failure]
    assert flags[0].field_path == "header.ara_toplam"


def test_out_of_scope_document_never_reaches_extraction() -> None:
    # Metin katmani olmayan belge ingestion'da durur; sagalayiciya gonderilmez.
    inspection = inspect_pdf(image_only_pdf())
    assert inspection.accepted is False
    assert inspection.reason is not None


def test_chain_is_deterministic() -> None:
    extractor = RecordedExtractor(wire_json(wire_payload()))
    request = _request()

    def run() -> tuple[object, ...]:
        result = extractor.extract(request)
        assert result.invoice is not None
        report = validate_invoice(result.invoice)
        return build_review_flags(result.invoice, report, parse_failures=result.parse_failures)

    assert run() == run()
