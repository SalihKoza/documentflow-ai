"""Wire payload -> ExtractionResult cevrimi (uretim yolunun kendisi test edilir)."""

from datetime import date
from decimal import Decimal

import pytest

from documentflow.extraction import (
    ExtractionStatus,
    ProviderMetadata,
    build_result,
    fake_metadata,
)
from documentflow.extraction.mapping import _HEADER_KINDS, _LINE_KINDS
from documentflow.schema import FieldStatus, InvoiceHeader, LineItem
from tests.extraction._fixtures import (
    line_payload,
    missing_field,
    ok_field,
    unreadable_field,
    wire_json,
    wire_payload,
)

METADATA = fake_metadata("recorded")


def run(payload: dict) -> object:
    return build_result(wire_json(payload), METADATA)


# --- Gecerli payload ------------------------------------------------------------------


def test_valid_payload_produces_ok_result() -> None:
    result = run(wire_payload())
    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None
    assert result.parse_failures == ()
    assert result.error_detail is None


def test_numeric_values_become_decimal_not_float() -> None:
    invoice = run(wire_payload()).invoice
    assert invoice is not None
    total = invoice.header.genel_toplam.value
    assert isinstance(total, Decimal)
    assert not isinstance(total, float)
    assert total == Decimal("3600.00")


def test_date_value_is_parsed() -> None:
    invoice = run(wire_payload()).invoice
    assert invoice is not None
    assert invoice.header.fatura_tarihi.value == date(2025, 3, 15)


def test_percent_sign_in_raw_is_parsed_as_rate() -> None:
    invoice = run(wire_payload()).invoice
    assert invoice is not None
    assert invoice.kalemler.value is not None
    assert invoice.kalemler.value[0].kdv_orani.value == Decimal("20")


def test_multiple_lines_are_mapped_in_order() -> None:
    payload = wire_payload()
    payload["kalemler"]["value"] = [
        line_payload(satir_tutari=ok_field("1.000,00")),
        line_payload(satir_tutari=ok_field("2.000,00")),
    ]
    invoice = run(payload).invoice
    assert invoice is not None
    assert invoice.kalemler.value is not None
    totals = [line.satir_tutari.value for line in invoice.kalemler.value]
    assert totals == [Decimal("1000.00"), Decimal("2000.00")]


def test_empty_line_list_is_accepted() -> None:
    payload = wire_payload()
    payload["kalemler"]["value"] = []
    result = run(payload)
    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None
    assert result.invoice.kalemler.value == []


# --- Float korumasi -------------------------------------------------------------------


def test_json_number_value_is_rejected() -> None:
    # Sozlesme "sayilari metin olarak dondur" der; JSON sayisi Python'da float olur
    # ve semadaki Decimal korumasini (D-017) bozardi.
    payload = wire_payload()
    payload["header"]["genel_toplam"]["value"] = 3600.00
    result = run(payload)
    assert result.status is ExtractionStatus.schema_mismatch


# --- Bicimsiz / sozlesme disi yanitlar -------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["", "not json at all", "{", '{"schema_version": "0.1",}', "[]"],
)
def test_invalid_or_non_object_json(text: str) -> None:
    result = build_result(text, METADATA)
    assert result.status in {ExtractionStatus.invalid_json, ExtractionStatus.schema_mismatch}
    assert result.invoice is None


def test_unparseable_json_is_invalid_json() -> None:
    assert build_result("{ bozuk", METADATA).status is ExtractionStatus.invalid_json


def test_extra_header_field_is_schema_mismatch() -> None:
    payload = wire_payload()
    payload["header"]["ekstra_alan"] = ok_field("x")
    assert run(payload).status is ExtractionStatus.schema_mismatch


def test_llm_confidence_field_is_rejected_not_ignored() -> None:
    # PROJECT_BRIEF §5: model kaynakli confidence sessizce yutulmaz.
    payload = wire_payload()
    payload["header"]["fatura_no"]["confidence"] = 0.98
    result = run(payload)
    assert result.status is ExtractionStatus.schema_mismatch


def test_top_level_confidence_field_is_rejected() -> None:
    payload = wire_payload()
    payload["confidence"] = 0.91
    assert run(payload).status is ExtractionStatus.schema_mismatch


def test_unknown_status_value_is_schema_mismatch() -> None:
    payload = wire_payload()
    payload["header"]["fatura_no"]["status"] = "belki"
    assert run(payload).status is ExtractionStatus.schema_mismatch


def test_schema_version_mismatch_is_rejected() -> None:
    payload = wire_payload()
    payload["schema_version"] = "9.9"
    result = run(payload)
    assert result.status is ExtractionStatus.schema_mismatch
    assert result.error_detail == "schema_version: unexpected_value"


def test_kalemler_ok_without_value_is_schema_mismatch() -> None:
    payload = wire_payload()
    payload["kalemler"]["value"] = None
    result = run(payload)
    assert result.status is ExtractionStatus.schema_mismatch
    assert result.error_detail == "kalemler: ok_without_value"


def test_status_invariant_violation_is_schema_mismatch() -> None:
    # missing dedigi halde raw gonderen sagalayici yapisal invariant'i ihlal eder.
    payload = wire_payload()
    payload["header"]["fatura_no"] = {"raw": "ABC", "value": None, "status": "missing"}
    assert run(payload).status is ExtractionStatus.schema_mismatch


def test_error_detail_does_not_leak_document_values() -> None:
    secret = "COK-GIZLI-UNVAN-12345"
    payload = wire_payload()
    payload["header"]["satici_unvan"] = ok_field(secret)
    payload["header"]["ekstra_alan"] = ok_field(secret)
    result = run(payload)
    assert result.status is ExtractionStatus.schema_mismatch
    assert result.error_detail is not None
    assert secret not in result.error_detail
    assert "extra_forbidden" in result.error_detail


# --- missing / unreadable / parse dusurme ---------------------------------------------


def test_missing_field_is_carried_through() -> None:
    payload = wire_payload()
    payload["header"]["fatura_no"] = missing_field()
    invoice = run(payload).invoice
    assert invoice is not None
    assert invoice.header.fatura_no.status is FieldStatus.missing
    assert invoice.header.fatura_no.value is None


def test_unreadable_field_is_carried_through() -> None:
    payload = wire_payload()
    payload["header"]["genel_toplam"] = unreadable_field("3.6OO,OO")
    invoice = run(payload).invoice
    assert invoice is not None
    assert invoice.header.genel_toplam.status is FieldStatus.unreadable
    assert invoice.header.genel_toplam.raw == "3.6OO,OO"


def test_unavailable_line_item_container_is_carried_through() -> None:
    payload = wire_payload()
    payload["kalemler"] = {"raw": None, "value": None, "status": "missing"}
    invoice = run(payload).invoice
    assert invoice is not None
    assert invoice.kalemler.status is FieldStatus.missing


def test_ok_but_unparseable_number_is_downgraded_to_unreadable() -> None:
    payload = wire_payload()
    payload["header"]["ara_toplam"] = ok_field("uc bin lira", "uc bin lira")
    result = run(payload)
    assert result.status is ExtractionStatus.ok
    assert result.invoice is not None
    field = result.invoice.header.ara_toplam
    assert field.status is FieldStatus.unreadable
    assert field.value is None
    assert field.raw == "uc bin lira"
    assert result.parse_failures == ("header.ara_toplam",)


def test_ok_but_unparseable_date_is_downgraded() -> None:
    payload = wire_payload()
    payload["header"]["fatura_tarihi"] = ok_field("31.13.2025")
    result = run(payload)
    assert result.parse_failures == ("header.fatura_tarihi",)


def test_ok_but_blank_text_is_downgraded() -> None:
    payload = wire_payload()
    payload["header"]["satici_unvan"] = ok_field("   ", "   raw   ")
    result = run(payload)
    assert result.parse_failures == ("header.satici_unvan",)


def test_line_level_parse_failure_path_is_indexed() -> None:
    payload = wire_payload()
    payload["kalemler"]["value"] = [
        line_payload(),
        line_payload(birim_fiyat=ok_field("bin bes yuz")),
    ]
    result = run(payload)
    assert result.parse_failures == ("kalemler[1].birim_fiyat",)


def test_parse_failures_preserve_field_order() -> None:
    payload = wire_payload()
    payload["header"]["kdv_toplam"] = ok_field("abc")
    payload["header"]["ara_toplam"] = ok_field("xyz")
    result = run(payload)
    # InvoiceHeader bildirim sirasi: ara_toplam, kdv_toplam
    assert result.parse_failures == ("header.ara_toplam", "header.kdv_toplam")


# --- Sozlesme butunlugu ---------------------------------------------------------------


def test_field_kind_maps_cover_the_schema() -> None:
    # Sema alani eklenip burasi guncellenmezse cevrim sessizce eksik kalirdi.
    assert set(_HEADER_KINDS) == set(InvoiceHeader.model_fields)
    assert set(_LINE_KINDS) == set(LineItem.model_fields)


def test_metadata_is_carried_into_result() -> None:
    metadata = ProviderMetadata(
        provider="recorded",
        model="test-model",
        prompt_version="p1",
        latency_ms=42,
        input_tokens=100,
        output_tokens=20,
        estimated_cost_usd=Decimal("0.0012"),
    )
    result = build_result(wire_json(wire_payload()), metadata)
    assert result.metadata.latency_ms == 42
    assert result.metadata.estimated_cost_usd == Decimal("0.0012")
    assert result.metadata.model == "test-model"
