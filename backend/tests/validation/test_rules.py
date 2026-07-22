"""Tek tek kural davranislari (FastAPI ve veritabani olmadan, saf sentetik veri)."""

from decimal import Decimal

import pytest

from documentflow.schema import FieldValue
from documentflow.validation import (
    NotEvaluableReason,
    NotEvaluated,
    Severity,
    ValidationFinding,
    ValidationReport,
    validate_invoice,
)
from tests.validation._fixtures import (
    INVALID_TCKN,
    INVALID_VKN,
    VALID_TCKN,
    invoice,
    line,
    missing,
    ok,
    unreadable,
)


def rule_ids(report: ValidationReport) -> list[str]:
    return [finding.rule_id for finding in report.findings]


def skipped_ids(report: ValidationReport) -> list[str]:
    return [entry.rule_id for entry in report.not_evaluated]


def only(report: ValidationReport, rule_id: str) -> ValidationFinding:
    """Verilen kuraldan tam olarak bir bulgu bekler ve onu dondurur."""
    matches = [finding for finding in report.findings if finding.rule_id == rule_id]
    assert len(matches) == 1, f"{rule_id} icin tek bulgu bekleniyordu: {rule_ids(report)}"
    return matches[0]


def skipped(report: ValidationReport, rule_id: str) -> NotEvaluated:
    """Verilen kuraldan tam olarak bir not_evaluated kaydi bekler ve onu dondurur."""
    matches = [entry for entry in report.not_evaluated if entry.rule_id == rule_id]
    assert len(matches) == 1, f"{rule_id} icin tek kayit bekleniyordu: {skipped_ids(report)}"
    return matches[0]


_UNAVAILABLE = [
    (missing(), NotEvaluableReason.missing_field),
    (unreadable("###"), NotEvaluableReason.unreadable_field),
]


# --- Temiz fatura --------------------------------------------------------------------


def test_clean_invoice_produces_no_findings() -> None:
    report = validate_invoice(invoice())
    assert report.findings == ()
    assert report.not_evaluated == ()
    assert report.review_required is False


# --- FNO-001: fatura numarasi --------------------------------------------------------


@pytest.mark.parametrize("fatura_no", ["ABC2025000000123", "XYZ0000000000000", "ZZZ9999999999999"])
def test_fatura_no_matching_e_fatura_format_passes(fatura_no: str) -> None:
    assert "FNO-001" not in rule_ids(validate_invoice(invoice(fatura_no=ok(fatura_no))))


@pytest.mark.parametrize(
    "fatura_no",
    [
        "abc2025000000123",  # kucuk harf
        "AB2025000000123",  # 2 harf (15 karakter)
        "ABCD2025000000123",  # 4 harf (17 karakter)
        "ABC202500000012",  # 12 rakam
        "ABC20250000001234",  # 14 rakam
        "A-2025/000123",  # kagit fatura seri/sira
        "ABC2025 000000123",  # bosluk
        "ABC2025000000123 ",  # sondaki bosluk
        "ABÇ2025000000123",  # Turkce harf (A-Z disi)
    ],
)
def test_fatura_no_deviation_is_warning_not_error(fatura_no: str) -> None:
    report = validate_invoice(invoice(fatura_no=ok(fatura_no)))
    finding = only(report, "FNO-001")
    assert finding.severity is Severity.warning
    assert finding.field_paths == ("header.fatura_no",)


def test_fatura_no_never_produces_error() -> None:
    report = validate_invoice(invoice(fatura_no=ok("!!!")))
    assert [f.severity for f in report.findings] == [Severity.warning]


@pytest.mark.parametrize(("field", "reason"), _UNAVAILABLE)
def test_fatura_no_unavailable_is_not_evaluable(
    field: FieldValue, reason: NotEvaluableReason
) -> None:
    report = validate_invoice(invoice(fatura_no=field))
    assert "FNO-001" not in rule_ids(report)
    entry = skipped(report, "FNO-001")
    assert entry.reason is reason
    assert entry.field_paths == ("header.fatura_no",)


# --- VKN-001 / VKN-002: satici_vkn ---------------------------------------------------


def test_satici_vkn_bad_checksum_is_error() -> None:
    report = validate_invoice(invoice(satici_vkn=ok(INVALID_VKN)))
    finding = only(report, "VKN-002")
    assert finding.severity is Severity.error
    assert finding.field_paths == ("header.satici_vkn",)


@pytest.mark.parametrize("value", ["123456789", "12345678901", "12345678a0", "123456 789"])
def test_satici_vkn_bad_format_reports_format_rule_only(value: str) -> None:
    report = validate_invoice(invoice(satici_vkn=ok(value)))
    assert rule_ids(report) == ["VKN-001"]
    # Kaskad atlama (bicim bozuk -> checksum calisamaz) not_evaluated'a yazilmaz.
    assert "VKN-002" not in skipped_ids(report)


@pytest.mark.parametrize(("field", "reason"), _UNAVAILABLE)
def test_satici_vkn_unavailable_is_not_evaluable(
    field: FieldValue, reason: NotEvaluableReason
) -> None:
    report = validate_invoice(invoice(satici_vkn=field))
    assert rule_ids(report) == []
    assert skipped(report, "VKN-001").reason is reason


# --- alici_vkn_tckn: uzunluga gore dispatch ------------------------------------------


def test_alici_valid_tckn_passes() -> None:
    assert rule_ids(validate_invoice(invoice(alici_vkn_tckn=ok(VALID_TCKN)))) == []


def test_alici_tckn_bad_checksum_is_error() -> None:
    report = validate_invoice(invoice(alici_vkn_tckn=ok(INVALID_TCKN)))
    finding = only(report, "TCKN-002")
    assert finding.severity is Severity.error
    assert finding.field_paths == ("header.alici_vkn_tckn",)


def test_alici_eleven_digits_starting_with_zero_is_tckn_format_error() -> None:
    assert rule_ids(validate_invoice(invoice(alici_vkn_tckn=ok("01234567890")))) == ["TCKN-001"]


def test_alici_ten_digit_bad_checksum_uses_vkn_rules() -> None:
    assert rule_ids(validate_invoice(invoice(alici_vkn_tckn=ok(INVALID_VKN)))) == ["VKN-002"]


def test_alici_ten_character_non_digit_uses_vkn_format_rule() -> None:
    # Uzunluk 10 oldugu icin VKN'ye dispatch edilir; bicim kurali devreye girer.
    assert rule_ids(validate_invoice(invoice(alici_vkn_tckn=ok("ABCDEFGHIJ")))) == ["VKN-001"]


@pytest.mark.parametrize("value", ["123456789", "123456789012", "1", "12345678 901"])
def test_alici_length_neither_ten_nor_eleven_is_id_error(value: str) -> None:
    finding = only(validate_invoice(invoice(alici_vkn_tckn=ok(value))), "ID-001")
    assert finding.severity is Severity.error
    assert finding.field_paths == ("header.alici_vkn_tckn",)


def test_alici_unavailable_is_not_evaluable() -> None:
    report = validate_invoice(invoice(alici_vkn_tckn=missing()))
    assert rule_ids(report) == []
    assert skipped(report, "ID-001").reason is NotEvaluableReason.missing_field


# --- KDV-001: oran kumesi ------------------------------------------------------------


@pytest.mark.parametrize("rate", ["1", "10", "20", "20.00", "1.0", "10.000"])
def test_allowed_kdv_rates_pass_regardless_of_scale(rate: str) -> None:
    sample = invoice(lines=[line(kdv_orani=ok(Decimal(rate), f"%{rate}"))])
    assert "KDV-001" not in rule_ids(validate_invoice(sample))


@pytest.mark.parametrize("rate", ["0", "8", "18", "2", "19.5", "100", "-20"])
def test_out_of_scope_kdv_rate_is_warning(rate: str) -> None:
    sample = invoice(lines=[line(kdv_orani=ok(Decimal(rate), f"%{rate}"))])
    finding = only(validate_invoice(sample), "KDV-001")
    assert finding.severity is Severity.warning
    assert finding.field_paths == ("kalemler[0].kdv_orani",)


@pytest.mark.parametrize(("field", "reason"), _UNAVAILABLE)
def test_kdv_rate_unavailable_is_not_evaluable(
    field: FieldValue, reason: NotEvaluableReason
) -> None:
    report = validate_invoice(invoice(lines=[line(kdv_orani=field)]))
    assert "KDV-001" not in rule_ids(report)
    entry = skipped(report, "KDV-001")
    assert entry.reason is reason
    assert entry.field_paths == ("kalemler[0].kdv_orani",)


# --- ARITH-001: ara_toplam + kdv_toplam == genel_toplam ------------------------------


@pytest.mark.parametrize(
    ("ara", "kdv", "genel"),
    [
        ("3000.00", "600.00", "3600.00"),
        ("3000", "600", "3600"),
        ("3000.000", "600.0", "3600"),  # farkli scale, ayni deger
        ("0.00", "0.00", "0.00"),
    ],
)
def test_header_totals_consistent(ara: str, kdv: str, genel: str) -> None:
    sample = invoice(
        ara_toplam=ok(Decimal(ara)),
        kdv_toplam=ok(Decimal(kdv)),
        genel_toplam=ok(Decimal(genel)),
        lines=[line(satir_tutari=ok(Decimal(ara)))],
    )
    assert "ARITH-001" not in rule_ids(validate_invoice(sample))


@pytest.mark.parametrize(
    ("ara", "kdv", "genel"),
    [("3000.00", "600.00", "3599.00"), ("3000.00", "600.00", "3600.01"), ("100", "20", "0")],
)
def test_header_totals_inconsistent_is_error(ara: str, kdv: str, genel: str) -> None:
    sample = invoice(
        ara_toplam=ok(Decimal(ara)),
        kdv_toplam=ok(Decimal(kdv)),
        genel_toplam=ok(Decimal(genel)),
        lines=[line(satir_tutari=ok(Decimal(ara)))],
    )
    finding = only(validate_invoice(sample), "ARITH-001")
    assert finding.severity is Severity.error
    assert finding.field_paths == (
        "header.genel_toplam",
        "header.ara_toplam",
        "header.kdv_toplam",
    )


def test_header_totals_missing_input_is_not_evaluable() -> None:
    report = validate_invoice(invoice(genel_toplam=missing()))
    assert "ARITH-001" not in rule_ids(report)
    entry = skipped(report, "ARITH-001")
    assert entry.reason is NotEvaluableReason.missing_field
    assert entry.field_paths == ("header.genel_toplam",)


def test_header_totals_unreadable_input_is_not_evaluable() -> None:
    report = validate_invoice(invoice(kdv_toplam=unreadable("6OO,OO")))
    entry = skipped(report, "ARITH-001")
    assert entry.reason is NotEvaluableReason.unreadable_field
    assert entry.field_paths == ("header.kdv_toplam",)


def test_missing_takes_precedence_over_unreadable_in_reason() -> None:
    report = validate_invoice(invoice(ara_toplam=unreadable("3.OOO"), genel_toplam=missing()))
    entry = skipped(report, "ARITH-001")
    assert entry.reason is NotEvaluableReason.missing_field
    # Bloke eden TUM alanlar, girdi bildirim sirasinda kaydedilir.
    assert entry.field_paths == ("header.ara_toplam", "header.genel_toplam")


# --- ARITH-003: miktar x birim_fiyat == satir_tutari ---------------------------------


@pytest.mark.parametrize(
    ("miktar", "birim_fiyat", "satir_tutari"),
    [("2", "1500.00", "3000.00"), ("1", "3000", "3000.0000"), ("0", "1500.00", "0")],
)
def test_line_product_consistent(miktar: str, birim_fiyat: str, satir_tutari: str) -> None:
    sample = invoice(
        lines=[
            line(
                miktar=ok(Decimal(miktar)),
                birim_fiyat=ok(Decimal(birim_fiyat)),
                satir_tutari=ok(Decimal(satir_tutari)),
            )
        ],
        ara_toplam=ok(Decimal(satir_tutari)),
        kdv_toplam=ok(Decimal("0")),
        genel_toplam=ok(Decimal(satir_tutari)),
    )
    assert "ARITH-003" not in rule_ids(validate_invoice(sample))


def test_line_product_inconsistent_is_error() -> None:
    sample = invoice(
        lines=[line(satir_tutari=ok(Decimal("2999.00")))],
        ara_toplam=ok(Decimal("2999.00")),
        kdv_toplam=ok(Decimal("601.00")),
    )
    finding = only(validate_invoice(sample), "ARITH-003")
    assert finding.severity is Severity.error
    assert finding.field_paths == (
        "kalemler[0].satir_tutari",
        "kalemler[0].miktar",
        "kalemler[0].birim_fiyat",
    )


def test_line_product_unavailable_input_is_not_evaluable() -> None:
    report = validate_invoice(invoice(lines=[line(birim_fiyat=unreadable("1.5OO,OO"))]))
    assert "ARITH-003" not in rule_ids(report)
    entry = skipped(report, "ARITH-003")
    assert entry.reason is NotEvaluableReason.unreadable_field
    assert entry.field_paths == ("kalemler[0].birim_fiyat",)


# --- ARITH-002: toplam satir tutari == ara_toplam ------------------------------------


def test_multi_line_sum_consistent() -> None:
    sample = invoice(
        lines=[
            line(satir_tutari=ok(Decimal("1000.00")), birim_fiyat=ok(Decimal("500.00"))),
            line(satir_tutari=ok(Decimal("2000.00")), birim_fiyat=ok(Decimal("1000.00"))),
        ]
    )
    assert rule_ids(validate_invoice(sample)) == []


def test_multi_line_sum_inconsistent_is_error() -> None:
    sample = invoice(
        lines=[
            line(satir_tutari=ok(Decimal("1000.00")), birim_fiyat=ok(Decimal("500.00"))),
            line(satir_tutari=ok(Decimal("1500.00")), birim_fiyat=ok(Decimal("750.00"))),
        ]
    )
    finding = only(validate_invoice(sample), "ARITH-002")
    assert finding.severity is Severity.error
    assert finding.field_paths == (
        "header.ara_toplam",
        "kalemler[0].satir_tutari",
        "kalemler[1].satir_tutari",
    )


def test_line_sum_scale_difference_is_not_a_finding() -> None:
    sample = invoice(
        ara_toplam=ok(Decimal("3000")),
        lines=[line(satir_tutari=ok(Decimal("3000.0000")))],
    )
    assert "ARITH-002" not in rule_ids(validate_invoice(sample))


def test_line_sum_skipped_when_any_line_total_unavailable() -> None:
    sample = invoice(lines=[line(), line(satir_tutari=missing(), birim_fiyat=ok(Decimal("1.00")))])
    report = validate_invoice(sample)
    assert "ARITH-002" not in rule_ids(report)
    entry = skipped(report, "ARITH-002")
    assert entry.reason is NotEvaluableReason.missing_field
    assert entry.field_paths == ("kalemler[1].satir_tutari",)


def test_line_sum_skipped_when_ara_toplam_unavailable() -> None:
    entry = skipped(validate_invoice(invoice(ara_toplam=missing())), "ARITH-002")
    assert entry.field_paths == ("header.ara_toplam",)
