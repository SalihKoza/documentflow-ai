"""validate_invoice() agregasyon davranisi: sira, tekrarsizlik, determinizm, kapsam."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from documentflow.schema import FieldValue
from documentflow.validation import (
    RULESET_VERSION,
    NotEvaluableReason,
    Severity,
    ValidationReport,
    validate_invoice,
)
from documentflow.validation import rules as rules_module
from tests.validation._fixtures import INVALID_VKN, invoice, line, missing, ok, unreadable


def many_violations() -> ValidationReport:
    """Her kural ailesinden en az bir ihlal iceren iki satirli fatura."""
    sample = invoice(
        fatura_no=ok("A-2025/1"),
        satici_vkn=ok(INVALID_VKN),
        alici_vkn_tckn=ok("123456789"),
        genel_toplam=ok(Decimal("3599.00")),
        lines=[
            line(kdv_orani=ok(Decimal("8")), satir_tutari=ok(Decimal("2999.00"))),
            line(kdv_orani=ok(Decimal("18")), satir_tutari=ok(Decimal("2.00"))),
        ],
    )
    return validate_invoice(sample)


# --- Rapor kabugu --------------------------------------------------------------------


def test_report_carries_ruleset_version() -> None:
    assert validate_invoice(invoice()).ruleset_version == RULESET_VERSION == "0.1"


def test_report_has_no_confidence_like_field() -> None:
    dumped = many_violations().model_dump()
    assert set(dumped) == {"ruleset_version", "findings", "not_evaluated", "review_required"}
    serialized = repr(dumped).lower()
    for banned in ("confidence", "probability", "score", "olasilik"):
        assert banned not in serialized


def test_review_required_is_false_only_when_no_findings() -> None:
    assert validate_invoice(invoice()).review_required is False
    # Yalnizca not_evaluated varsa review gerekmez: bulgu uretilmemistir.
    assert validate_invoice(invoice(fatura_no=missing())).review_required is False
    # Tek bir warning bile review'a yonlendirir.
    warning_only = validate_invoice(invoice(lines=[line(kdv_orani=ok(Decimal("8")))]))
    assert [f.severity for f in warning_only.findings] == [Severity.warning]
    assert warning_only.review_required is True


# --- Deterministik sira ve tekrarsizlik ----------------------------------------------


def test_findings_follow_fixed_rule_order() -> None:
    assert [f.rule_id for f in many_violations().findings] == [
        "FNO-001",
        "VKN-002",
        "ID-001",
        "ARITH-001",
        "KDV-001",
        "ARITH-003",
        "KDV-001",
        "ARITH-003",
        "ARITH-002",
    ]


def test_line_findings_follow_ascending_index_order() -> None:
    findings = many_violations().findings
    anchors = [f.field_paths[0] for f in findings if f.field_paths[0].startswith("kalemler")]
    assert anchors == [
        "kalemler[0].kdv_orani",
        "kalemler[0].satir_tutari",
        "kalemler[1].kdv_orani",
        "kalemler[1].satir_tutari",
    ]


def test_no_duplicate_finding() -> None:
    keys = [(f.rule_id, f.field_paths) for f in many_violations().findings]
    assert len(set(keys)) == len(keys)


def test_no_duplicate_not_evaluated_entry() -> None:
    report = validate_invoice(
        invoice(kalemler=missing(), ara_toplam=missing(), fatura_no=missing())
    )
    keys = [(e.rule_id, e.field_paths, e.reason) for e in report.not_evaluated]
    assert len(set(keys)) == len(keys)


def test_repeated_runs_produce_identical_reports() -> None:
    sample = invoice(
        fatura_no=ok("A-2025/1"),
        satici_vkn=ok(INVALID_VKN),
        lines=[line(kdv_orani=ok(Decimal("8"))), line(satir_tutari=unreadable("3.OOO"))],
    )
    first = validate_invoice(sample)
    second = validate_invoice(sample)
    assert first == second
    assert first.model_dump() == second.model_dump()


def test_validation_does_not_mutate_the_invoice() -> None:
    sample = invoice(satici_vkn=ok(INVALID_VKN))
    before = sample.model_dump()
    validate_invoice(sample)
    assert sample.model_dump() == before


# --- Kalem container durumlari -------------------------------------------------------


def test_empty_line_item_list_makes_line_sum_not_evaluable() -> None:
    report = validate_invoice(invoice(kalemler=ok([], "Kalem tablosu bulundu, satir cikarilamadi")))
    assert report.findings == ()
    assert [(e.rule_id, e.field_paths, e.reason) for e in report.not_evaluated] == [
        ("ARITH-002", ("kalemler",), NotEvaluableReason.no_line_items)
    ]


@pytest.mark.parametrize(
    ("container", "reason"),
    [
        (missing(), NotEvaluableReason.missing_field),
        (unreadable("... tablo ..."), NotEvaluableReason.unreadable_field),
    ],
)
def test_unavailable_container_skips_all_line_rules(
    container: FieldValue, reason: NotEvaluableReason
) -> None:
    report = validate_invoice(invoice(kalemler=container))
    assert report.findings == ()
    # Satir kurallari hic calismaz; yalnizca toplam kurali kaydedilir.
    assert [(e.rule_id, e.field_paths, e.reason) for e in report.not_evaluated] == [
        ("ARITH-002", ("kalemler",), reason)
    ]


def test_many_lines_are_all_evaluated() -> None:
    lines = [
        line(
            miktar=ok(Decimal("1")),
            birim_fiyat=ok(Decimal("100.00")),
            satir_tutari=ok(Decimal("100.00")),
        )
        for _ in range(12)
    ]
    report = validate_invoice(
        invoice(
            lines=lines,
            ara_toplam=ok(Decimal("1200.00")),
            kdv_toplam=ok(Decimal("240.00")),
            genel_toplam=ok(Decimal("1440.00")),
        )
    )
    assert report.findings == ()
    assert report.not_evaluated == ()


# --- Kapsam kilidi -------------------------------------------------------------------


def test_validation_package_has_no_framework_imports() -> None:
    """Validation katmani FastAPI/DB/LLM saglayicisindan bagimsiz kalmalidir."""
    forbidden = {"fastapi", "starlette", "sqlalchemy", "alembic", "psycopg", "uvicorn", "httpx"}
    package_dir = Path(rules_module.__file__).parent
    for path in sorted(package_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                root = module.split(".")[0]
                assert root not in forbidden, f"{path.name} icinde yasak import: {module}"
