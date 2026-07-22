"""Validation testleri icin sentetik fatura kurucu yardimcilar.

TUM degerler sentetiktir. VKN/TCKN vektorleri gercek bir belgeden kopyalanmamis,
checksum algoritmasindan TURETILMISTIR (bkz. test_identifiers.py'deki tekillik
testleri) ve hicbir isim, adres veya belge ile iliskili degildir.

Varsayilan `invoice()` tum kurallardan temiz gecer; testler yalnizca ilgilendikleri
alani override eder.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from documentflow.schema import FieldStatus, FieldValue, Invoice, InvoiceHeader, LineItem

# Checksum'i gecerli sentetik kimlikler.
VALID_VKN = "1234567890"
VALID_ALICI_VKN = "9876543217"
VALID_TCKN = "10000000146"
# Checksum'i BOZUK (son hanesi degistirilmis) karsilikari.
INVALID_VKN = "1234567891"
INVALID_TCKN = "10000000147"

# e-Fatura bicimi: 3 buyuk harf + 13 rakam.
VALID_FATURA_NO = "ABC2025000000123"


def ok(value: Any, raw: str | None = None) -> FieldValue:
    """status=ok bir FieldValue (raw verilmezse degerin metin hali kullanilir)."""
    return FieldValue(
        raw=raw if raw is not None else str(value), value=value, status=FieldStatus.ok
    )


def missing() -> FieldValue:
    """status=missing: alan belgede hic yoktu."""
    return FieldValue(raw=None, value=None, status=FieldStatus.missing)


def unreadable(raw: str = "???") -> FieldValue:
    """status=unreadable: alan vardi ama guvenilir bicimde parse edilemedi."""
    return FieldValue(raw=raw, value=None, status=FieldStatus.unreadable)


def line(**overrides: FieldValue) -> LineItem:
    """Tek kalem: 2 x 1.500,00 = 3.000,00, KDV %20 (kendi icinde tutarli)."""
    fields: dict[str, FieldValue] = {
        "aciklama": ok("Danismanlik Hizmeti"),
        "miktar": ok(Decimal("2"), "2"),
        "birim_fiyat": ok(Decimal("1500.00"), "1.500,00"),
        "kdv_orani": ok(Decimal("20"), "%20"),
        "satir_tutari": ok(Decimal("3000.00"), "3.000,00"),
    }
    fields.update(overrides)
    return LineItem(**fields)


def header(**overrides: FieldValue) -> InvoiceHeader:
    """Ara 3.000,00 + KDV 600,00 = Genel 3.600,00 (kendi icinde tutarli)."""
    fields: dict[str, FieldValue] = {
        "fatura_no": ok(VALID_FATURA_NO),
        "fatura_tarihi": ok(date(2025, 3, 15), "15.03.2025"),
        "satici_unvan": ok("ACME Bilisim Ltd. Sti."),
        "satici_vkn": ok(VALID_VKN),
        "alici_unvan": ok("Beta Ticaret A.S."),
        "alici_vkn_tckn": ok(VALID_ALICI_VKN),
        "ara_toplam": ok(Decimal("3000.00"), "3.000,00"),
        "kdv_toplam": ok(Decimal("600.00"), "600,00"),
        "genel_toplam": ok(Decimal("3600.00"), "3.600,00"),
    }
    fields.update(overrides)
    return InvoiceHeader(**fields)


def invoice(
    *,
    lines: list[LineItem] | None = None,
    kalemler: FieldValue | None = None,
    **header_overrides: FieldValue,
) -> Invoice:
    """Varsayilan olarak tek kalemli, tum kurallardan temiz gecen bir fatura.

    `lines` kalem listesini, `kalemler` ise container FieldValue'sunu (missing/
    unreadable senaryolari icin) dogrudan degistirir.
    """
    if kalemler is None:
        kalemler = ok(
            [line()] if lines is None else lines,
            "Danismanlik Hizmeti 2 1.500,00 %20 3.000,00",
        )
    return Invoice(header=header(**header_overrides), kalemler=kalemler)
