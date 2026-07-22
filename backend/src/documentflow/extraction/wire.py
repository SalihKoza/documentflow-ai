"""Sagalayicinin uretmesi gereken JSON sozlesmesi (wire DTO).

Bu, domain modelinin (`documentflow.schema`) DISARI DONUK karsiligidir. Ayri
tutulmasinin iki nedeni var:

1. **Float tuzagi (D-017).** JSON sayilari Python'da `float` olur ve semadaki
   `Numeric` BeforeValidator'i float'i reddeder. Bu yuzden wire DTO'sunda TUM
   sayisal alanlar `str`'dir; metin -> Decimal cevrimini mapping katmani mevcut
   `parse_tr_number`/`parse_tr_date` ile yapar. Sagalayiciya "sayiyi metin olarak
   dondur" demek, tum zinciri float'tan uzak tutmanin en basit yoludur.
2. **Sozlesme sikiligi.** Tum DTO'lar `extra="forbid"` tasir; sagalayici fazladan
   bir alan (ornegin `confidence`) donderirse sonuc sessizce kabul edilmez,
   `schema_mismatch` olur (PROJECT_BRIEF §5).

`status` icin domain enum'u (`FieldStatus`) yeniden kullanilir: tanimsiz bir durum
degeri Pydantic tarafindan reddedilir.
"""

from pydantic import BaseModel, ConfigDict

from documentflow.schema import FieldStatus


class WireField(BaseModel):
    """Tek bir cikarilan alan. `value` HER ZAMAN metindir (sayi bile olsa)."""

    model_config = ConfigDict(extra="forbid")

    raw: str | None = None
    value: str | None = None
    status: FieldStatus


class WireLineItem(BaseModel):
    """Fatura kalemi - semadaki bes alanin birebir karsiligi (D-018)."""

    model_config = ConfigDict(extra="forbid")

    aciklama: WireField
    miktar: WireField
    birim_fiyat: WireField
    kdv_orani: WireField
    satir_tutari: WireField


class WireHeader(BaseModel):
    """Fatura basligi - semadaki dokuz kanonik alan."""

    model_config = ConfigDict(extra="forbid")

    fatura_no: WireField
    fatura_tarihi: WireField
    satici_unvan: WireField
    satici_vkn: WireField
    alici_unvan: WireField
    alici_vkn_tckn: WireField
    ara_toplam: WireField
    kdv_toplam: WireField
    genel_toplam: WireField


class WireLineItems(BaseModel):
    """Kalem container'i (D-019): raw = tablo metni, value = satirlar."""

    model_config = ConfigDict(extra="forbid")

    raw: str | None = None
    value: list[WireLineItem] | None = None
    status: FieldStatus


class WireInvoice(BaseModel):
    """Sagalayicidan beklenen tam JSON govdesi."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    header: WireHeader
    kalemler: WireLineItems
