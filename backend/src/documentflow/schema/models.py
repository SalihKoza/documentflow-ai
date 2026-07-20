"""Extraction semasi domain modelleri (v0.1).

InvoiceHeader (dokuz alan), LineItem (bes alan - K5) ve Invoice. Her cikarilan
alan FieldValue ile sarilir. schema_version bir metadata alanidir (FieldValue
degildir); dondurulmus kontrat surumunu tasir.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from documentflow.schema.types import FieldValue, Numeric


class LineItem(BaseModel):
    """Fatura kalemi (K5 - tam olarak bu bes alan)."""

    model_config = ConfigDict(extra="forbid")

    aciklama: FieldValue[str]
    miktar: FieldValue[Numeric]
    birim_fiyat: FieldValue[Numeric]
    kdv_orani: FieldValue[Numeric]  # puan: Decimal("20") == %20
    satir_tutari: FieldValue[Numeric]


class InvoiceHeader(BaseModel):
    """Fatura baslik alanlari (tam olarak dokuz alan)."""

    model_config = ConfigDict(extra="forbid")

    fatura_no: FieldValue[str]
    fatura_tarihi: FieldValue[date]
    satici_unvan: FieldValue[str]
    satici_vkn: FieldValue[str]
    alici_unvan: FieldValue[str]
    alici_vkn_tckn: FieldValue[str]
    ara_toplam: FieldValue[Numeric]
    kdv_toplam: FieldValue[Numeric]
    genel_toplam: FieldValue[Numeric]


class Invoice(BaseModel):
    """Cikarilan fatura: baslik + kalemler.

    kalemler bir FieldValue[list[LineItem]]'dir: container raw'i tum tablo metni,
    status'u ok/missing/unreadable'dir. Satir bazli ayri ham metin tutulmaz (K5).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.1"
    header: InvoiceHeader
    kalemler: FieldValue[list[LineItem]]
