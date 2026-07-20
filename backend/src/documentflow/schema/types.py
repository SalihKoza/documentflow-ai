"""Extraction semasi cekirdek tipleri (v0.1).

FieldStatus ve FieldValue[T]: her cikarilan alan ham (raw) ve parse edilmis
(value) degeri, uclu bir durum (status) ile birlikte tasir (K2/K3). Buradaki
kurallar YAPISAL butunluk invariant'laridir; is (business) validation degildir.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator, model_validator


class FieldStatus(StrEnum):
    """Bir alanin cikarim durumu (K3)."""

    ok = "ok"
    missing = "missing"
    unreadable = "unreadable"


def _reject_float(v: Any) -> Any:
    """Decimal alanlarina float girisini reddeder (K4/T5).

    Decimal(float) ikili yuvarlama hatasini kaliciligina alir; bu yuzden float
    yolu tamamen kapalidir. str, int ve Decimal serbesttir.
    """
    if isinstance(v, float):
        raise ValueError("Decimal alanlari float kabul etmez; str/int/Decimal kullanin")
    return v


# Semadaki tum sayisal alanlar icin tek Decimal tipi: float reddedilir.
Numeric = Annotated[Decimal, BeforeValidator(_reject_float)]


class FieldValue[T](BaseModel):
    """Ham + parse edilmis deger + durum uclusu (K2/K3).

    Yapisal invariant'lar:
      ok         -> raw != None  ve  value != None
      unreadable -> raw != None  ve  value == None
      missing    -> raw == None  ve  value == None
    raw ya None'dur ya da whitespace-strip sonrasi bos olmayan bir metindir;
    "" ve yalnizca bosluk iceren metin None'a indirgenir. value non-None ancak
    ve ancak status == ok oldugunda.
    """

    model_config = ConfigDict(extra="forbid")

    raw: str | None = None
    value: T | None = None
    status: FieldStatus

    @field_validator("raw")
    @classmethod
    def _normalize_raw(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v if v.strip() != "" else None

    @model_validator(mode="after")
    def _check_invariants(self) -> "FieldValue[T]":
        if self.status is FieldStatus.ok:
            if self.raw is None or self.value is None:
                raise ValueError("status=ok icin hem raw hem value zorunludur")
        elif self.status is FieldStatus.unreadable:
            if self.raw is None or self.value is not None:
                raise ValueError("status=unreadable icin raw zorunlu, value None olmali")
        else:  # missing
            if self.raw is not None or self.value is not None:
                raise ValueError("status=missing icin raw ve value None olmali")
        return self
