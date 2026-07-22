"""Deterministik flag uretimi (saf, framework ve sagalayici bagimsiz).

Girdi yalnizca iki deterministik kaynaktan gelir: cikarim ciktisinin ALAN DURUMLARI
(`FieldStatus`) ve `documentflow.validation` raporu. LLM confidence, olasilik ya da
model tabanli herhangi bir skor KULLANILMAZ (PROJECT_BRIEF §5).

Sira insa yoluyla sabittir; rapor sonradan siralanmaz.
"""

from collections.abc import Sequence
from typing import Any

from documentflow.flagging.types import (
    FlagSeverity,
    FlagSignal,
    ReviewAction,
    ReviewFlag,
)
from documentflow.schema import FieldStatus, FieldValue, Invoice, InvoiceHeader, LineItem
from documentflow.validation import NotEvaluableReason, Severity, ValidationReport

# Validation kural kimligi -> (sinyal, onerilen eylem). Ruleset 0.1'in tamamini
# kapsar; kapsamadigi bir kimlik gelirse katalog disi catch-all kullanilir.
_RULE_SIGNALS: dict[str, tuple[FlagSignal, ReviewAction]] = {
    "VKN-001": (FlagSignal.identifier_format, ReviewAction.correct_identifier),
    "VKN-002": (FlagSignal.identifier_checksum, ReviewAction.correct_identifier),
    "TCKN-001": (FlagSignal.identifier_format, ReviewAction.correct_identifier),
    "TCKN-002": (FlagSignal.identifier_checksum, ReviewAction.correct_identifier),
    "ID-001": (FlagSignal.identifier_format, ReviewAction.correct_identifier),
    "FNO-001": (FlagSignal.invoice_number_format, ReviewAction.confirm_invoice_number),
    "KDV-001": (FlagSignal.kdv_rate_out_of_scope, ReviewAction.confirm_vat_rate),
    "ARITH-001": (FlagSignal.header_arithmetic, ReviewAction.confirm_totals),
    "ARITH-002": (FlagSignal.line_sum_mismatch, ReviewAction.confirm_totals),
    "ARITH-003": (FlagSignal.line_arithmetic, ReviewAction.confirm_totals),
}

_UNCLASSIFIED_RULE = (
    FlagSignal.validation_finding,
    ReviewAction.verify_field_against_document,
)

_STATUS_REASONS: dict[FlagSignal, str] = {
    FlagSignal.field_missing: "Alan belgede bulunamadi; degerin belgeden dogrulanmasi gerekiyor",
    FlagSignal.field_unreadable: "Alan belgede var fakat guvenilir bicimde okunamadi",
    FlagSignal.parse_failure: (
        "Cikarim alani okundu olarak isaretledi, fakat degeri beklenen bicimde "
        "parse edilemedi; deger tahmin edilmedi"
    ),
}

_NO_LINE_ITEMS_REASON = (
    "Kalem tablosu bulundu fakat satir cikarilamadi; bu yapi v0.1 kapsaminda otomatik dogrulanamaz"
)


def _status_signal(
    field: FieldValue[Any], path: str, parse_failures: set[str]
) -> FlagSignal | None:
    """Alan durumundan sinyal turetir; alan `ok` ise None."""
    if field.status is FieldStatus.missing:
        return FlagSignal.field_missing
    if field.status is FieldStatus.unreadable:
        # Parse dusurmesi daha spesifik bir aciklamadir: model alani okuduk dedi
        # ama deger cevrilemedi. Ayni yol icin iki flag uretilmez.
        if path in parse_failures:
            return FlagSignal.parse_failure
        return FlagSignal.field_unreadable
    return None


def _status_flag(field: FieldValue[Any], path: str, parse_failures: set[str]) -> ReviewFlag | None:
    signal = _status_signal(field, path, parse_failures)
    if signal is None:
        return None
    return ReviewFlag(
        field_path=path,
        signal_code=signal,
        severity=FlagSeverity.review,
        reason=_STATUS_REASONS[signal],
        originating_rule=None,
        suggested_action=ReviewAction.verify_field_against_document,
    )


def _deduplicate(flags: Sequence[ReviewFlag]) -> tuple[ReviewFlag, ...]:
    """`(field_path, signal_code, originating_rule)` ucluleri tekil olur; ilk kalir."""
    seen: set[tuple[str, FlagSignal, str | None]] = set()
    unique: list[ReviewFlag] = []
    for flag in flags:
        key = (flag.field_path, flag.signal_code, flag.originating_rule)
        if key in seen:
            continue
        seen.add(key)
        unique.append(flag)
    return tuple(unique)


def build_review_flags(
    invoice: Invoice,
    report: ValidationReport,
    *,
    parse_failures: Sequence[str] = (),
) -> tuple[ReviewFlag, ...]:
    """Cikarim ciktisi ve validation raporundan review flag'leri uretir.

    Sira insa yoluyladir: header alanlari `InvoiceHeader` bildirim sirasinda ->
    kalem container'i -> satirlar index artan -> validation bulgulari (rapor
    sirasinda) -> kapsam disi yapi kayitlari. Ayni girdi ayni ciktiyi verir.

    `parse_failures`, extraction mapping katmaninin `ok`'tan `unreadable`'a
    dusurdugu alan yollaridir (bkz. `ExtractionResult.parse_failures`).
    """
    failure_paths = set(parse_failures)
    flags: list[ReviewFlag] = []

    for name in InvoiceHeader.model_fields:
        flag = _status_flag(getattr(invoice.header, name), f"header.{name}", failure_paths)
        if flag is not None:
            flags.append(flag)

    container_flag = _status_flag(invoice.kalemler, "kalemler", failure_paths)
    if container_flag is not None:
        flags.append(container_flag)

    if invoice.kalemler.status is FieldStatus.ok and invoice.kalemler.value is not None:
        for index, line in enumerate(invoice.kalemler.value):
            for name in LineItem.model_fields:
                flag = _status_flag(getattr(line, name), f"kalemler[{index}].{name}", failure_paths)
                if flag is not None:
                    flags.append(flag)

    for finding in report.findings:
        signal, action = _RULE_SIGNALS.get(finding.rule_id, _UNCLASSIFIED_RULE)
        flags.append(
            ReviewFlag(
                field_path=finding.field_paths[0],
                signal_code=signal,
                severity=(
                    FlagSeverity.blocking
                    if finding.severity is Severity.error
                    else FlagSeverity.review
                ),
                reason=finding.message,
                originating_rule=finding.rule_id,
                suggested_action=action,
            )
        )

    # Degerlendirilemeyen kurallardan yalnizca kapsam disi YAPI sinyali cikarilir.
    # missing/unreadable nedenli kayitlar zaten alan durumu flag'i uretmistir;
    # onlari tekrar raporlamak cift kayit olurdu (P3'teki kaskad kuralinin aynisi).
    for entry in report.not_evaluated:
        if entry.reason is NotEvaluableReason.no_line_items:
            flags.append(
                ReviewFlag(
                    field_path=entry.field_paths[0],
                    signal_code=FlagSignal.unsupported_scope_structure,
                    severity=FlagSeverity.review,
                    reason=_NO_LINE_ITEMS_REASON,
                    originating_rule=entry.rule_id,
                    suggested_action=ReviewAction.manual_entry_out_of_scope,
                )
            )

    return _deduplicate(flags)
