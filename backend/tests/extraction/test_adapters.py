"""Fake ve recorded adapter davranisi + ExtractionResult invariant'lari.

Hicbir test API anahtari, ag erisimi veya veritabani gerektirmez.
"""

import pytest
from pydantic import ValidationError

from documentflow.extraction import (
    ExtractionRequest,
    ExtractionResult,
    ExtractionStatus,
    ExtractorProtocol,
    FakeExtractor,
    RecordedExtractor,
    build_result,
    fake_metadata,
)
from tests.extraction._fixtures import wire_json, wire_payload

REQUEST = ExtractionRequest(document_id="FZ-TEST-001", content=b"%PDF-1.4 sentetik")


def _ok_result() -> ExtractionResult:
    return build_result(wire_json(wire_payload()), fake_metadata())


# --- Protokol uyumu -------------------------------------------------------------------


def test_adapters_satisfy_the_protocol_without_inheritance() -> None:
    assert isinstance(FakeExtractor(_ok_result()), ExtractorProtocol)
    assert isinstance(RecordedExtractor(wire_json(wire_payload())), ExtractorProtocol)


# --- FakeExtractor --------------------------------------------------------------------


def test_fake_returns_configured_result_and_records_requests() -> None:
    expected = _ok_result()
    extractor = FakeExtractor(expected)
    assert extractor.extract(REQUEST) == expected
    assert extractor.requests == [REQUEST]


@pytest.mark.parametrize(
    "status",
    [
        ExtractionStatus.provider_error,
        ExtractionStatus.timeout,
        ExtractionStatus.refused,
        ExtractionStatus.truncated,
        ExtractionStatus.invalid_json,
        ExtractionStatus.schema_mismatch,
    ],
)
def test_fake_can_produce_every_failure_status(status: ExtractionStatus) -> None:
    result = FakeExtractor.failing(status, error_detail="sentetik").extract(REQUEST)
    assert result.status is status
    assert result.invoice is None
    assert result.error_detail == "sentetik"


def test_fake_failing_rejects_ok_status() -> None:
    with pytest.raises(ValueError):
        FakeExtractor.failing(ExtractionStatus.ok)


# --- RecordedExtractor ----------------------------------------------------------------


def test_recorded_runs_the_production_conversion_path() -> None:
    extractor = RecordedExtractor(wire_json(wire_payload()))
    result = extractor.extract(REQUEST)
    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None
    assert extractor.requests == [REQUEST]


def test_recorded_surfaces_invalid_json_from_the_real_path() -> None:
    assert RecordedExtractor("{ bozuk").extract(REQUEST).status is ExtractionStatus.invalid_json


def test_recorded_is_deterministic() -> None:
    extractor = RecordedExtractor(wire_json(wire_payload()))
    assert extractor.extract(REQUEST) == extractor.extract(REQUEST)


# --- ExtractionResult invariant'lari ---------------------------------------------------


def test_ok_without_invoice_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(status=ExtractionStatus.ok, invoice=None, metadata=fake_metadata())


def test_failure_with_invoice_is_rejected() -> None:
    invoice = _ok_result().invoice
    with pytest.raises(ValidationError):
        ExtractionResult(status=ExtractionStatus.timeout, invoice=invoice, metadata=fake_metadata())


def test_failure_with_parse_failures_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(
            status=ExtractionStatus.timeout,
            invoice=None,
            metadata=fake_metadata(),
            parse_failures=("header.fatura_no",),
        )


# --- Gizlilik ve sozlesme -------------------------------------------------------------


def test_request_repr_does_not_expose_document_bytes() -> None:
    request = ExtractionRequest(document_id="FZ-TEST-002", content=b"%PDF-GIZLI-ICERIK")
    assert "GIZLI" not in repr(request)


def test_provider_metadata_has_no_confidence_like_field() -> None:
    dumped = fake_metadata().model_dump()
    serialized = repr(dumped).lower()
    for banned in ("confidence", "probability", "score", "olasilik"):
        assert banned not in serialized
