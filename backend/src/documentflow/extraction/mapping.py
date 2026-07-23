"""Wire DTO -> domain `Invoice` cevrimi (saf, deterministik).

Bu modul cikarim zincirinin TEK dogruluk noktasidir: hem kayitli yanit (recorded)
adapter'i hem de ileride eklenecek gercek sagalayici adapter'i `build_result`
cagirir. Boylece "gecersiz JSON", "sema uyusmazligi" gibi senaryolar mock'la
degil, uretimde calisan yolla test edilir.

Iki davranis kurali:

- **Tahmin yok.** Sagalayici `ok` dedigi halde deger parse edilemiyorsa alan
  sessizce doldurulmaz; `unreadable`'a dusurulur ve yolu `parse_failures`'a yazilir
  (EVALUATION §1 seviye B'deki "sessiz yanlis parse kabul edilmez" kurali).
- **Belge icerigi hata metnine sizmaz.** Pydantic dogrulama hatalari girdi
  degerlerini icerir; bu yuzden `error_detail` yalnizca alan yolu + hata TURU
  ozetinden olusturulur (`_summarize_validation_error`).
"""

import json
from datetime import date
from decimal import Decimal
from enum import Enum, auto
from typing import Any

from pydantic import ValidationError

from documentflow.extraction.types import (
    ExtractionResult,
    ExtractionStatus,
    ProviderMetadata,
)
from documentflow.extraction.wire import WireField, WireInvoice, WireLineItems
from documentflow.parsing import parse_tr_date, parse_tr_number
from documentflow.schema import FieldStatus, FieldValue, Invoice, InvoiceHeader, LineItem

# error_detail'de en fazla kac dogrulama hatasi ozetlenir (metni kisa tutar).
_MAX_SUMMARIZED_ERRORS = 5


class WireContractError(ValueError):
    """Wire DTO'su sema kontratini ihlal etti; Invoice'a cevrilemez.

    Mesaj yalnizca alan yolu ve hata kodu icerir; belge degeri icermez.
    """


class _Kind(Enum):
    """Bir alanin metin -> deger cevriminde hangi parser'i kullanacagi."""

    text = auto()
    date = auto()
    numeric = auto()


# Alan adi -> cevrim turu. Anahtar kumeleri semadaki model alanlariyla birebir
# ayni olmalidir; bir test bunu dogrular (sema degisirse burasi sessizce eskimez).
_HEADER_KINDS: dict[str, _Kind] = {
    "fatura_no": _Kind.text,
    "fatura_tarihi": _Kind.date,
    "satici_unvan": _Kind.text,
    "satici_vkn": _Kind.text,
    "alici_unvan": _Kind.text,
    "alici_vkn_tckn": _Kind.text,
    "ara_toplam": _Kind.numeric,
    "kdv_toplam": _Kind.numeric,
    "genel_toplam": _Kind.numeric,
}

_LINE_KINDS: dict[str, _Kind] = {
    "aciklama": _Kind.text,
    "miktar": _Kind.numeric,
    "birim_fiyat": _Kind.numeric,
    "kdv_orani": _Kind.numeric,
    "satir_tutari": _Kind.numeric,
}


class UnknownFieldPathError(ValueError):
    """Verilen alan yolu semada tanimli degil."""


def _kind_for_path(field_path: str) -> _Kind:
    """`header.<alan>` / `kalemler[<i>].<alan>` yolundan cevrim turunu bulur."""
    head, _, name = field_path.rpartition(".")
    if head == "header":
        kind = _HEADER_KINDS.get(name)
    elif head.startswith("kalemler[") and head.endswith("]"):
        kind = _LINE_KINDS.get(name)
    else:
        kind = None
    if kind is None:
        raise UnknownFieldPathError(field_path)
    return kind


def parse_field_value(field_path: str, text: str) -> str | date | Decimal | None:
    """Bir alan yolu icin metni hedef tipe cevirir; cevrilemezse None.

    Cikarim ciktisini cevirirken kullanilan mantigin AYNISI insan duzeltmelerinde
    de kullanilsin diye disari acilir: duzeltilen bir deger, modelin urettigi bir
    deger ile ayni parser'dan gecer.
    """
    return _parse_value(text, _kind_for_path(field_path))


def _parse_value(value: str | None, kind: _Kind) -> str | date | Decimal | None:
    """Metni hedef tipe cevirir; cevrilemezse None (istisna degil, D-020)."""
    if value is None:
        return None
    if kind is _Kind.text:
        # Yalnizca bosluktan olusan bir "deger" anlamli bir metin degildir.
        return value if value.strip() else None
    if kind is _Kind.date:
        return parse_tr_date(value)
    return parse_tr_number(value)


def _convert_field(
    field: WireField, path: str, kind: _Kind, parse_failures: list[str]
) -> FieldValue[Any]:
    """Tek bir wire alanini FieldValue'ya cevirir.

    `missing`/`unreadable` oldugu gibi tasinir. `ok` fakat deger parse edilemiyorsa
    alan `unreadable`'a DUSURULUR ve yolu `parse_failures`'a eklenir.
    """
    if field.status is not FieldStatus.ok:
        return FieldValue(raw=field.raw, value=None, status=field.status)

    parsed = _parse_value(field.value, kind)
    if parsed is None:
        parse_failures.append(path)
        return FieldValue(raw=field.raw, value=None, status=FieldStatus.unreadable)
    return FieldValue(raw=field.raw, value=parsed, status=FieldStatus.ok)


def _convert_line_items(
    wire: WireLineItems, parse_failures: list[str]
) -> FieldValue[list[LineItem]]:
    """Kalem container'ini cevirir (D-019)."""
    if wire.status is not FieldStatus.ok:
        return FieldValue(raw=wire.raw, value=None, status=wire.status)
    if wire.value is None:
        raise WireContractError("kalemler: ok_without_value")

    lines = [
        LineItem(
            **{
                name: _convert_field(
                    getattr(item, name), f"kalemler[{index}].{name}", kind, parse_failures
                )
                for name, kind in _LINE_KINDS.items()
            }
        )
        for index, item in enumerate(wire.value)
    ]
    return FieldValue(raw=wire.raw, value=lines, status=FieldStatus.ok)


def wire_to_invoice(
    wire: WireInvoice, parse_failures: list[str], *, expected_schema_version: str
) -> Invoice:
    """Dogrulanmis wire DTO'sunu domain `Invoice`'ina cevirir.

    Yapisal ihlallerde `WireContractError` veya Pydantic `ValidationError` firlatir;
    cagiran bunlari `schema_mismatch` sonucuna cevirir.
    """
    if wire.schema_version != expected_schema_version:
        raise WireContractError("schema_version: unexpected_value")

    header = InvoiceHeader(
        **{
            name: _convert_field(getattr(wire.header, name), f"header.{name}", kind, parse_failures)
            for name, kind in _HEADER_KINDS.items()
        }
    )
    return Invoice(
        schema_version=wire.schema_version,
        header=header,
        kalemler=_convert_line_items(wire.kalemler, parse_failures),
    )


def _summarize_validation_error(error: ValidationError) -> str:
    """Dogrulama hatalarini DEGER SIZDIRMADAN ozetler.

    Yalnizca `loc` (alan yolu) ve `type` (kararli hata kodu) kullanilir; Pydantic'in
    `msg`/`input` alanlari belge icerigi tasiyabildigi icin disarida birakilir.
    """
    entries = error.errors()
    summarized = [
        f"{'.'.join(str(part) for part in entry['loc']) or '<root>'}: {entry['type']}"
        for entry in entries[:_MAX_SUMMARIZED_ERRORS]
    ]
    if len(entries) > _MAX_SUMMARIZED_ERRORS:
        summarized.append(f"(+{len(entries) - _MAX_SUMMARIZED_ERRORS} hata daha)")
    return "; ".join(summarized)


def _failure(status: ExtractionStatus, metadata: ProviderMetadata, detail: str) -> ExtractionResult:
    return ExtractionResult(status=status, invoice=None, metadata=metadata, error_detail=detail)


def build_result(response_text: str, metadata: ProviderMetadata) -> ExtractionResult:
    """Sagalayicinin ham metin yanitini `ExtractionResult`'a cevirir.

    Saf ve deterministiktir: ag erisimi yoktur, ayni girdi ayni ciktiyi verir.
    Gercek adapter de kayitli-yanit adapter'i de bu fonksiyonu cagirir.
    """
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return _failure(
            ExtractionStatus.invalid_json,
            metadata,
            f"{exc.msg} (satir {exc.lineno}, sutun {exc.colno})",
        )

    try:
        wire = WireInvoice.model_validate(payload)
    except ValidationError as exc:
        return _failure(
            ExtractionStatus.schema_mismatch, metadata, _summarize_validation_error(exc)
        )

    parse_failures: list[str] = []
    try:
        invoice = wire_to_invoice(
            wire, parse_failures, expected_schema_version=metadata.schema_version
        )
    except WireContractError as exc:
        return _failure(ExtractionStatus.schema_mismatch, metadata, str(exc))
    except ValidationError as exc:
        return _failure(
            ExtractionStatus.schema_mismatch, metadata, _summarize_validation_error(exc)
        )

    return ExtractionResult(
        status=ExtractionStatus.ok,
        invoice=invoice,
        metadata=metadata,
        parse_failures=tuple(parse_failures),
    )
