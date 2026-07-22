"""Deterministik flag uretimi.

Invoice fixture'lari validation testleriyle paylasilir (tests/validation/_fixtures.py)
- ayni sentetik fatura kurucusu iki katmanda da kullanilir.
"""

from decimal import Decimal

import pytest

from documentflow.flagging import (
    FlagSeverity,
    FlagSignal,
    ReviewAction,
    ReviewFlag,
    build_review_flags,
)
from documentflow.validation import validate_invoice
from tests.validation._fixtures import (
    INVALID_VKN,
    invoice,
    line,
    missing,
    ok,
    unreadable,
)


def flags_for(sample: object, **kwargs: object) -> tuple[ReviewFlag, ...]:
    return build_review_flags(sample, validate_invoice(sample), **kwargs)  # type: ignore[arg-type]


def signals(items: tuple[ReviewFlag, ...]) -> list[FlagSignal]:
    return [flag.signal_code for flag in items]


def paths(items: tuple[ReviewFlag, ...]) -> list[str]:
    return [flag.field_path for flag in items]


# --- Temiz fatura ---------------------------------------------------------------------


def test_clean_invoice_produces_no_flags() -> None:
    assert flags_for(invoice()) == ()


# --- Alan durumu kaynakli flag'ler ----------------------------------------------------


def test_missing_field_produces_a_review_flag() -> None:
    result = flags_for(invoice(satici_unvan=missing()))
    assert len(result) == 1
    flag = result[0]
    assert flag.field_path == "header.satici_unvan"
    assert flag.signal_code is FlagSignal.field_missing
    assert flag.severity is FlagSeverity.review
    assert flag.originating_rule is None
    assert flag.suggested_action is ReviewAction.verify_field_against_document
    assert flag.reason


def test_unreadable_field_produces_a_review_flag() -> None:
    result = flags_for(invoice(satici_unvan=unreadable("???")))
    assert signals(result) == [FlagSignal.field_unreadable]


def test_unavailable_line_container_is_flagged_once() -> None:
    result = flags_for(invoice(kalemler=missing()))
    assert paths(result) == ["kalemler"]
    assert signals(result) == [FlagSignal.field_missing]


def test_line_field_paths_are_indexed() -> None:
    sample = invoice(lines=[line(), line(aciklama=missing())])
    result = flags_for(sample)
    assert "kalemler[1].aciklama" in paths(result)


# --- parse_failure, field_unreadable'in yerini alir -------------------------------------


def test_parse_failure_replaces_the_generic_unreadable_signal() -> None:
    sample = invoice(satici_unvan=unreadable("   bozuk   "))
    result = flags_for(sample, parse_failures=["header.satici_unvan"])
    assert signals(result) == [FlagSignal.parse_failure]
    # Ayni alan icin iki ayri flag uretilmez.
    assert len(result) == 1


def test_parse_failure_for_another_field_does_not_leak() -> None:
    sample = invoice(satici_unvan=unreadable("???"))
    result = flags_for(sample, parse_failures=["header.alici_unvan"])
    assert signals(result) == [FlagSignal.field_unreadable]


# --- Validation bulgusu kaynakli flag'ler ---------------------------------------------


def test_checksum_error_becomes_a_blocking_flag() -> None:
    result = flags_for(invoice(satici_vkn=ok(INVALID_VKN)))
    assert len(result) == 1
    flag = result[0]
    assert flag.signal_code is FlagSignal.identifier_checksum
    assert flag.severity is FlagSeverity.blocking
    assert flag.originating_rule == "VKN-002"
    assert flag.suggested_action is ReviewAction.correct_identifier


def test_identifier_format_error_maps_to_format_signal() -> None:
    result = flags_for(invoice(satici_vkn=ok("12345")))
    assert signals(result) == [FlagSignal.identifier_format]
    assert result[0].originating_rule == "VKN-001"


def test_warning_finding_becomes_review_severity() -> None:
    result = flags_for(invoice(fatura_no=ok("A-2025/1")))
    assert signals(result) == [FlagSignal.invoice_number_format]
    assert result[0].severity is FlagSeverity.review
    assert result[0].suggested_action is ReviewAction.confirm_invoice_number


def test_out_of_scope_vat_rate_maps_to_review() -> None:
    result = flags_for(invoice(lines=[line(kdv_orani=ok(Decimal("8")))]))
    assert signals(result) == [FlagSignal.kdv_rate_out_of_scope]
    assert result[0].field_path == "kalemler[0].kdv_orani"
    assert result[0].severity is FlagSeverity.review


@pytest.mark.parametrize(
    ("rule_id", "signal"),
    [
        ("ARITH-001", FlagSignal.header_arithmetic),
        ("ARITH-002", FlagSignal.line_sum_mismatch),
        ("ARITH-003", FlagSignal.line_arithmetic),
    ],
)
def test_arithmetic_rules_map_to_distinct_signals(rule_id: str, signal: FlagSignal) -> None:
    samples = {
        "ARITH-001": invoice(genel_toplam=ok(Decimal("3599.00"))),
        "ARITH-002": invoice(
            lines=[line(satir_tutari=ok(Decimal("2999.00")), birim_fiyat=ok(Decimal("1499.50")))]
        ),
        "ARITH-003": invoice(
            lines=[line(satir_tutari=ok(Decimal("2999.00")))],
            ara_toplam=ok(Decimal("2999.00")),
            kdv_toplam=ok(Decimal("601.00")),
        ),
    }
    result = flags_for(samples[rule_id])
    matching = [flag for flag in result if flag.originating_rule == rule_id]
    assert len(matching) == 1
    assert matching[0].signal_code is signal
    assert matching[0].severity is FlagSeverity.blocking
    assert matching[0].suggested_action is ReviewAction.confirm_totals


# --- Kapsam disi yapi -----------------------------------------------------------------


def test_empty_line_list_flags_unsupported_scope_structure() -> None:
    result = flags_for(invoice(kalemler=ok([], "Kalem tablosu bulundu, satir cikarilamadi")))
    assert signals(result) == [FlagSignal.unsupported_scope_structure]
    assert result[0].field_path == "kalemler"
    assert result[0].originating_rule == "ARITH-002"
    assert result[0].suggested_action is ReviewAction.manual_entry_out_of_scope


def test_not_evaluated_due_to_missing_input_does_not_double_report() -> None:
    # ara_toplam missing -> alan durumu flag'i var; ARITH-001/002 not_evaluated
    # kayitlari AYRICA flag uretmez.
    result = flags_for(invoice(ara_toplam=missing()))
    assert signals(result) == [FlagSignal.field_missing]
    assert paths(result) == ["header.ara_toplam"]


# --- Sira, tekrarsizlik, determinizm --------------------------------------------------


def _many_signals() -> tuple[ReviewFlag, ...]:
    sample = invoice(
        fatura_no=ok("A-2025/1"),
        satici_vkn=ok(INVALID_VKN),
        alici_unvan=missing(),
        genel_toplam=ok(Decimal("3599.00")),
        lines=[
            line(kdv_orani=ok(Decimal("8")), satir_tutari=ok(Decimal("2999.00"))),
            line(kdv_orani=ok(Decimal("18")), satir_tutari=ok(Decimal("2.00"))),
        ],
    )
    return flags_for(sample)


def test_flags_follow_status_then_validation_order() -> None:
    result = _many_signals()
    assert signals(result) == [
        # 1. Alan durumu kaynakli (InvoiceHeader bildirim sirasinda)
        FlagSignal.field_missing,
        # 2. Validation bulgulari (rapor sirasinda)
        FlagSignal.invoice_number_format,
        FlagSignal.identifier_checksum,
        FlagSignal.header_arithmetic,
        FlagSignal.kdv_rate_out_of_scope,
        FlagSignal.line_arithmetic,
        FlagSignal.kdv_rate_out_of_scope,
        FlagSignal.line_arithmetic,
        FlagSignal.line_sum_mismatch,
    ]


def test_line_flags_are_index_ascending() -> None:
    anchors = [path for path in paths(_many_signals()) if path.startswith("kalemler[")]
    assert anchors == [
        "kalemler[0].kdv_orani",
        "kalemler[0].satir_tutari",
        "kalemler[1].kdv_orani",
        "kalemler[1].satir_tutari",
    ]


def test_no_duplicate_flags() -> None:
    keys = [(flag.field_path, flag.signal_code, flag.originating_rule) for flag in _many_signals()]
    assert len(set(keys)) == len(keys)


def test_repeated_runs_produce_identical_flags() -> None:
    assert _many_signals() == _many_signals()


def test_every_ruleset_finding_is_classified() -> None:
    # Katalog disi catch-all ruleset 0.1'de hic kullanilmamalidir.
    assert FlagSignal.validation_finding not in signals(_many_signals())
    identifier_cases = [
        invoice(alici_vkn_tckn=ok("123456789")),
        invoice(alici_vkn_tckn=ok("01234567890")),
        invoice(alici_vkn_tckn=ok("10000000147")),
    ]
    for sample in identifier_cases:
        assert FlagSignal.validation_finding not in signals(flags_for(sample))


# --- Confidence yasagi ----------------------------------------------------------------


def test_flag_carries_no_confidence_like_field() -> None:
    assert set(ReviewFlag.model_fields) == {
        "field_path",
        "signal_code",
        "severity",
        "reason",
        "originating_rule",
        "suggested_action",
    }
    serialized = repr([flag.model_dump() for flag in _many_signals()]).lower()
    for banned in ("confidence", "probability", "score", "olasilik"):
        assert banned not in serialized
