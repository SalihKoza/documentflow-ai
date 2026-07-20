"""FieldValue yapisal invariant testleri (business validation DEGIL)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from documentflow.schema import Invoice, InvoiceHeader, LineItem
from documentflow.schema.types import FieldStatus, FieldValue, Numeric


def test_ok_requires_raw_and_value() -> None:
    fv = FieldValue[str](raw="ACME", value="ACME", status=FieldStatus.ok)
    assert fv.raw == "ACME"
    assert fv.value == "ACME"


def test_missing_both_none() -> None:
    fv = FieldValue[str](raw=None, value=None, status=FieldStatus.missing)
    assert fv.raw is None
    assert fv.value is None


def test_unreadable_raw_present_value_none() -> None:
    fv = FieldValue[Numeric](raw="!!!", value=None, status=FieldStatus.unreadable)
    assert fv.raw == "!!!"
    assert fv.value is None


@pytest.mark.parametrize(
    ("raw", "value", "status"),
    [
        (None, "x", FieldStatus.ok),  # ok, raw yok
        ("x", None, FieldStatus.ok),  # ok, value yok
        ("x", "x", FieldStatus.missing),  # missing, raw dolu
        (None, "x", FieldStatus.missing),  # missing, value dolu
        (None, None, FieldStatus.unreadable),  # unreadable, raw yok
        ("x", "x", FieldStatus.unreadable),  # unreadable, value dolu
    ],
)
def test_invalid_combinations_raise(
    raw: str | None, value: str | None, status: FieldStatus
) -> None:
    with pytest.raises(ValidationError):
        FieldValue[str](raw=raw, value=value, status=status)


def test_whitespace_raw_normalized_to_none() -> None:
    fv = FieldValue[str](raw="   ", value=None, status=FieldStatus.missing)
    assert fv.raw is None


def test_whitespace_raw_with_ok_raises() -> None:
    with pytest.raises(ValidationError):
        FieldValue[str](raw="   ", value="x", status=FieldStatus.ok)


def test_decimal_field_rejects_float() -> None:
    with pytest.raises(ValidationError):
        FieldValue[Numeric](raw="20", value=1.5, status=FieldStatus.ok)


def test_decimal_field_accepts_decimal_str_int() -> None:
    from_decimal = FieldValue[Numeric](raw="20", value=Decimal("20"), status=FieldStatus.ok)
    from_str = FieldValue[Numeric](raw="20", value="20", status=FieldStatus.ok)
    from_int = FieldValue[Numeric](raw="20", value=20, status=FieldStatus.ok)
    assert from_decimal.value == Decimal("20")
    assert from_str.value == Decimal("20")
    assert from_int.value == Decimal("20")


# --- Float bypass regresyon testleri (Karar: Secenek B) --------------------------------
# Amac: float'in domain modellerine sizamadigini KILITLEMEK. Parametresiz (bare) bir
# FieldValue float tutabilir (Numeric BeforeValidator yalnizca FieldValue[Numeric]'te
# calisir), fakat bu instance FieldValue[Numeric] bekleyen bir model alanina verildiginde
# Pydantic onu yeniden dogrular ve float'i reddeder. Boylece pratik sizinti yoktur.


def _ok(value: object, raw: str = "x") -> FieldValue:
    """Test yardimcisi: gecerli bir ok FieldValue (bare, parametresiz)."""
    return FieldValue(raw=raw, value=value, status=FieldStatus.ok)


def test_bare_fieldvalue_can_hold_float_but_is_inert() -> None:
    # Standalone bare FieldValue float tutabilir; hicbir modele bagli olmadigi icin inerttir.
    bare = FieldValue(raw="2", value=2.0, status=FieldStatus.ok)
    assert isinstance(bare.value, float)


def test_bare_float_rejected_when_injected_into_line_item() -> None:
    bare_float = FieldValue(raw="2", value=2.0, status=FieldStatus.ok)
    with pytest.raises(ValidationError):
        LineItem(
            aciklama=_ok("Hizmet"),
            miktar=bare_float,  # float tasiyan bare instance -> model sinirinda revalidate
            birim_fiyat=_ok(Decimal("1")),
            kdv_orani=_ok(Decimal("20")),
            satir_tutari=_ok(Decimal("2")),
        )


def _valid_header_kwargs() -> dict[str, FieldValue]:
    """Gecerli bir InvoiceHeader icin kanonik alan adlariyla kwargs."""
    return {
        "fatura_no": _ok("F-1"),
        "fatura_tarihi": _ok(date(2025, 1, 1), "01.01.2025"),
        "satici_unvan": _ok("Satici"),
        "satici_vkn": _ok("1234567890"),
        "alici_unvan": _ok("Alici"),
        "alici_vkn_tckn": _ok("0987654321"),
        "ara_toplam": _ok(Decimal("3000.00")),
        "kdv_toplam": _ok(Decimal("600.00")),
        "genel_toplam": _ok(Decimal("3600.00")),
    }


def test_bare_float_rejected_when_injected_into_invoice_header() -> None:
    kwargs = _valid_header_kwargs()
    kwargs["ara_toplam"] = FieldValue(raw="2", value=2.0, status=FieldStatus.ok)  # float
    with pytest.raises(ValidationError):
        InvoiceHeader(**kwargs)


def test_invoice_header_rejects_old_field_names() -> None:
    # Eski adlar kanonik rename sonrasi extra="forbid" ile reddedilmeli.
    kwargs = _valid_header_kwargs()
    kwargs["alici_vkn"] = kwargs.pop("alici_vkn_tckn")  # eski ad
    kwargs["kdv_toplami"] = kwargs.pop("kdv_toplam")  # eski ad
    with pytest.raises(ValidationError):
        InvoiceHeader(**kwargs)


def test_invoice_serialization_uses_canonical_names() -> None:
    line = LineItem(
        aciklama=_ok("Hizmet"),
        miktar=_ok(Decimal("2")),
        birim_fiyat=_ok(Decimal("1500.00")),
        kdv_orani=_ok(Decimal("20")),
        satir_tutari=_ok(Decimal("3000.00")),
    )
    invoice = Invoice(
        header=InvoiceHeader(**_valid_header_kwargs()),
        kalemler=_ok([line], "Hizmet 2 1.500,00 %20 3.000,00"),
    )
    header_keys = invoice.model_dump()["header"].keys()
    assert "alici_vkn_tckn" in header_keys
    assert "kdv_toplam" in header_keys
    assert "alici_vkn" not in header_keys
    assert "kdv_toplami" not in header_keys
