"""Fatura is (business) kurallari ve agregasyonu (ruleset 0.1).

Saf ve framework-bagimsizdir: FastAPI, veritabani veya LLM saglayicisi import
edilmez, I/O yapilmaz, global durum tutulmaz. Tek giris noktasi
`validate_invoice(invoice)`; generic bir rule engine veya plugin sistemi YOKTUR
(kurallar bilincli olarak sabit ve okunabilir bir sirada cagrilir).

Yapisal invariant'lar (raw/value/status tutarliligi) bu katmanin isi DEGILDIR;
onlar `schema/types.py` icinde Pydantic tarafindan zorlanir. Burada yalnizca
alanlar ARASI matematik ve mantik kontrol edilir.

Tum sayisal karsilastirmalar `Decimal` ile TAM esitliktir. Tolerance veya
yuvarlama kurali v0.1'de tanimlanmamistir (bkz. docs/VALIDATION.md - bilinen
sinirlar); `Decimal("20.00") == Decimal("20")` sayisal olarak dogru oldugundan
scale farki tek basina bulgu uretmez.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from documentflow.schema import FieldStatus, FieldValue, Invoice, InvoiceHeader, LineItem
from documentflow.validation.identifiers import (
    has_tckn_format,
    has_vkn_format,
    tckn_checksum_ok,
    vkn_checksum_ok,
)
from documentflow.validation.types import (
    NotEvaluableReason,
    NotEvaluated,
    Severity,
    ValidationFinding,
    ValidationReport,
)

# v0.1 kapsamindaki KDV oranlari (yuzde puani, LineItem.kdv_orani ile ayni birim).
# Kume ruleset surumune baglidir; mevzuat degisirse ruleset surumu artirilir.
ALLOWED_KDV_RATES = (Decimal("1"), Decimal("10"), Decimal("20"))

# e-Fatura numarasi: 3 buyuk ASCII harf + 13 rakam (seri + yil + sira). Kagit
# fatura serbest seri/sira bicimleri bu kalibi saglamaz; bu yuzden sapma hard
# fail degil warning uretir.
_FATURA_NO_FORMAT = re.compile(r"\A[A-Z]{3}[0-9]{13}\Z")


@dataclass(frozen=True)
class _Blocked:
    """Bir kuralin girdisinin bulunmadigini anlatan ic sonuc tipi."""

    field_paths: tuple[str, ...]
    reason: NotEvaluableReason


def _blocked(entries: Sequence[tuple[str, FieldValue[Any]]]) -> _Blocked | None:
    """`ok` olmayan girdileri ozetler; hepsi `ok` ise `None` doner.

    Reason onceligi: bloke edenler arasinda en az bir `missing` varsa
    `missing_field`, aksi halde `unreadable_field`.
    """
    unavailable = [(path, fv) for path, fv in entries if fv.status is not FieldStatus.ok]
    if not unavailable:
        return None
    reason = (
        NotEvaluableReason.missing_field
        if any(fv.status is FieldStatus.missing for _, fv in unavailable)
        else NotEvaluableReason.unreadable_field
    )
    return _Blocked(tuple(path for path, _ in unavailable), reason)


def _resolve[T](entries: Sequence[tuple[str, FieldValue[T]]]) -> list[T] | _Blocked:
    """Girdi alanlarinin hepsi `ok` ise degerlerini, degilse `_Blocked` dondurur."""
    blocked = _blocked(entries)
    if blocked is not None:
        return blocked
    # status == ok, yapisal invariant geregi value non-None (schema/types.py).
    return [fv.value for _, fv in entries if fv.value is not None]


class _Collector:
    """Bulgulari ve degerlendirilemeyen kurallari uygulama sirasinda biriktirir."""

    def __init__(self) -> None:
        self.findings: list[ValidationFinding] = []
        self.not_evaluated: list[NotEvaluated] = []

    def add(
        self, rule_id: str, severity: Severity, field_paths: tuple[str, ...], message: str
    ) -> None:
        self.findings.append(
            ValidationFinding(
                rule_id=rule_id, severity=severity, field_paths=field_paths, message=message
            )
        )

    def skip(self, rule_id: str, blocked: _Blocked) -> None:
        self.not_evaluated.append(
            NotEvaluated(rule_id=rule_id, field_paths=blocked.field_paths, reason=blocked.reason)
        )


def _check_fatura_no(collector: _Collector, header: InvoiceHeader) -> None:
    """FNO-001: fatura numarasi e-Fatura bicimine uyuyor mu (warning)."""
    path = "header.fatura_no"
    resolved = _resolve(((path, header.fatura_no),))
    if isinstance(resolved, _Blocked):
        collector.skip("FNO-001", resolved)
        return
    (fatura_no,) = resolved
    if _FATURA_NO_FORMAT.match(fatura_no) is None:
        collector.add(
            "FNO-001",
            Severity.warning,
            (path,),
            "Fatura numarasi beklenen e-Fatura bicimine (3 buyuk harf + 13 rakam) uymuyor",
        )


def _check_vkn(collector: _Collector, path: str, value: str) -> None:
    """VKN-001 (bicim) ve VKN-002 (checksum). Bicim gecmezse checksum atlanir."""
    if not has_vkn_format(value):
        collector.add("VKN-001", Severity.error, (path,), "VKN 10 haneli rakam dizisi olmalidir")
        return
    if not vkn_checksum_ok(value):
        collector.add("VKN-002", Severity.error, (path,), "VKN checksum dogrulamasi basarisiz")


def _check_tckn(collector: _Collector, path: str, value: str) -> None:
    """TCKN-001 (bicim) ve TCKN-002 (checksum). Bicim gecmezse checksum atlanir."""
    if not has_tckn_format(value):
        collector.add(
            "TCKN-001",
            Severity.error,
            (path,),
            "TCKN 11 haneli rakam dizisi olmalidir ve ilk hane sifir olamaz",
        )
        return
    if not tckn_checksum_ok(value):
        collector.add("TCKN-002", Severity.error, (path,), "TCKN checksum dogrulamasi basarisiz")


def _check_satici_vkn(collector: _Collector, header: InvoiceHeader) -> None:
    """Satici her zaman tuzel/vergi mukellefidir: yalnizca VKN kurallari uygulanir."""
    path = "header.satici_vkn"
    resolved = _resolve(((path, header.satici_vkn),))
    if isinstance(resolved, _Blocked):
        collector.skip("VKN-001", resolved)
        return
    (value,) = resolved
    _check_vkn(collector, path, value)


def _check_alici_vkn_tckn(collector: _Collector, header: InvoiceHeader) -> None:
    """Alici kimligi uzunluga gore dispatch edilir: 10 -> VKN, 11 -> TCKN, aksi -> ID-001."""
    path = "header.alici_vkn_tckn"
    resolved = _resolve(((path, header.alici_vkn_tckn),))
    if isinstance(resolved, _Blocked):
        collector.skip("ID-001", resolved)
        return
    (value,) = resolved
    if len(value) == 10:
        _check_vkn(collector, path, value)
    elif len(value) == 11:
        _check_tckn(collector, path, value)
    else:
        collector.add(
            "ID-001",
            Severity.error,
            (path,),
            "Alici kimlik numarasi ne VKN (10 hane) ne TCKN (11 hane) bicimine uyuyor",
        )


def _check_header_totals(collector: _Collector, header: InvoiceHeader) -> None:
    """ARITH-001: ara_toplam + kdv_toplam == genel_toplam."""
    inputs = (
        ("header.ara_toplam", header.ara_toplam),
        ("header.kdv_toplam", header.kdv_toplam),
        ("header.genel_toplam", header.genel_toplam),
    )
    resolved = _resolve(inputs)
    if isinstance(resolved, _Blocked):
        collector.skip("ARITH-001", resolved)
        return
    ara, kdv, genel = resolved
    if ara + kdv != genel:
        collector.add(
            "ARITH-001",
            Severity.error,
            ("header.genel_toplam", "header.ara_toplam", "header.kdv_toplam"),
            f"ara_toplam + kdv_toplam ({ara + kdv}) genel_toplam ({genel}) ile esit degil",
        )


def _check_line(collector: _Collector, index: int, line: LineItem) -> None:
    """Tek bir kalem satiri: KDV-001 (oran kumesi) ve ARITH-003 (satir carpimi)."""
    prefix = f"kalemler[{index}]"

    rate_path = f"{prefix}.kdv_orani"
    resolved_rate = _resolve(((rate_path, line.kdv_orani),))
    if isinstance(resolved_rate, _Blocked):
        collector.skip("KDV-001", resolved_rate)
    else:
        (rate,) = resolved_rate
        # Decimal esitligi scale'den bagimsizdir: Decimal("20.00") in (..., Decimal("20")).
        if rate not in ALLOWED_KDV_RATES:
            collector.add(
                "KDV-001",
                Severity.warning,
                (rate_path,),
                f"KDV orani ({rate}) v0.1 izin verilen kume disinda: 1, 10, 20",
            )

    line_inputs = (
        (f"{prefix}.miktar", line.miktar),
        (f"{prefix}.birim_fiyat", line.birim_fiyat),
        (f"{prefix}.satir_tutari", line.satir_tutari),
    )
    resolved_line = _resolve(line_inputs)
    if isinstance(resolved_line, _Blocked):
        collector.skip("ARITH-003", resolved_line)
        return
    miktar, birim_fiyat, satir_tutari = resolved_line
    if miktar * birim_fiyat != satir_tutari:
        collector.add(
            "ARITH-003",
            Severity.error,
            (f"{prefix}.satir_tutari", f"{prefix}.miktar", f"{prefix}.birim_fiyat"),
            f"miktar x birim_fiyat ({miktar * birim_fiyat}) "
            f"satir_tutari ({satir_tutari}) ile esit degil",
        )


def _check_line_sum(collector: _Collector, invoice: Invoice) -> None:
    """ARITH-002: Sigma(satir_tutari) == ara_toplam.

    Ara toplam ve kalem container'i `ok` olmali, liste bos olmamali ve HER satirin
    `satir_tutari` degeri okunabilmis olmalidir; aksi halde toplam bilinemez.
    """
    inputs: tuple[tuple[str, FieldValue[Any]], ...] = (
        ("header.ara_toplam", invoice.header.ara_toplam),
        ("kalemler", invoice.kalemler),
    )
    blocked = _blocked(inputs)
    if blocked is not None:
        collector.skip("ARITH-002", blocked)
        return

    ara_toplam = invoice.header.ara_toplam.value
    lines = invoice.kalemler.value
    if ara_toplam is None or lines is None:
        return  # yapisal invariant geregi ulasilmaz; yalnizca tip daraltmasi icin

    if not lines:
        # Bos kume uzerinde toplam almak dejenere bir onculdur: extraction tabloyu
        # bulup satir cikaramamis olabilir. Uydurma celiski uretilmez.
        collector.skip("ARITH-002", _Blocked(("kalemler",), NotEvaluableReason.no_line_items))
        return

    line_totals = _resolve(
        tuple(
            (f"kalemler[{index}].satir_tutari", line.satir_tutari)
            for index, line in enumerate(lines)
        )
    )
    if isinstance(line_totals, _Blocked):
        collector.skip("ARITH-002", line_totals)
        return

    total = sum(line_totals, Decimal(0))
    if total != ara_toplam:
        paths = ("header.ara_toplam",) + tuple(
            f"kalemler[{index}].satir_tutari" for index in range(len(lines))
        )
        collector.add(
            "ARITH-002",
            Severity.error,
            paths,
            f"Satir tutarlari toplami ({total}) ara_toplam ({ara_toplam}) ile esit degil",
        )


def validate_invoice(invoice: Invoice) -> ValidationReport:
    """Bir faturayi ruleset 0.1 kurallariyla dogrular (saf, deterministik).

    Kurallar sabit bir sirada uygulanir ve rapor bu sirayi korur (sonradan
    siralama yapilmaz): once `InvoiceHeader` bildirim sirasinda alan kurallari,
    sonra header toplam aritmetigi, sonra index artan sirada satir kurallari, en
    sonda iki seviyeyi baglayan satir toplami kurali. Her kural her hedefe bir
    kez uygulandigi icin ayni (rule_id, field_paths) cifti tekrar etmez.

    Cikti LLM confidence veya olasilik degeri ICERMEZ (PROJECT_BRIEF §5).
    """
    collector = _Collector()

    _check_fatura_no(collector, invoice.header)
    _check_satici_vkn(collector, invoice.header)
    _check_alici_vkn_tckn(collector, invoice.header)
    _check_header_totals(collector, invoice.header)

    if invoice.kalemler.status is FieldStatus.ok and invoice.kalemler.value is not None:
        for index, line in enumerate(invoice.kalemler.value):
            _check_line(collector, index, line)

    _check_line_sum(collector, invoice)

    return ValidationReport(
        findings=tuple(collector.findings),
        not_evaluated=tuple(collector.not_evaluated),
    )
