"""Extraction testleri icin sentetik wire payload kuruculari.

Tum degerler sentetiktir ve gercek bir belgeden alinmamistir. Sayisal alanlar
sozlesme geregi METIN olarak verilir (bkz. `documentflow.extraction.wire`).
"""

import json
from typing import Any


def ok_field(value: str, raw: str | None = None) -> dict[str, Any]:
    """status=ok alan; raw verilmezse deger metninin kendisi kullanilir."""
    return {"raw": raw if raw is not None else value, "value": value, "status": "ok"}


def missing_field() -> dict[str, Any]:
    return {"raw": None, "value": None, "status": "missing"}


def unreadable_field(raw: str = "???") -> dict[str, Any]:
    return {"raw": raw, "value": None, "status": "unreadable"}


def line_payload(**overrides: dict[str, Any]) -> dict[str, Any]:
    """Kendi icinde tutarli kalem: 2 x 1.500,00 = 3.000,00, KDV %20."""
    line: dict[str, Any] = {
        "aciklama": ok_field("Danismanlik Hizmeti"),
        "miktar": ok_field("2"),
        "birim_fiyat": ok_field("1.500,00"),
        "kdv_orani": ok_field("20", "%20"),
        "satir_tutari": ok_field("3.000,00"),
    }
    line.update(overrides)
    return line


def wire_payload() -> dict[str, Any]:
    """Tum kurallardan temiz gecen, tek kalemli gecerli payload (her cagrida yeni)."""
    return {
        "schema_version": "0.1",
        "header": {
            "fatura_no": ok_field("ABC2025000000123"),
            "fatura_tarihi": ok_field("15.03.2025"),
            "satici_unvan": ok_field("ACME Bilisim Ltd. Sti."),
            "satici_vkn": ok_field("1234567890"),
            "alici_unvan": ok_field("Beta Ticaret A.S."),
            "alici_vkn_tckn": ok_field("9876543217"),
            "ara_toplam": ok_field("3.000,00"),
            "kdv_toplam": ok_field("600,00"),
            "genel_toplam": ok_field("3.600,00"),
        },
        "kalemler": {
            "raw": "Danismanlik Hizmeti 2 1.500,00 %20 3.000,00",
            "status": "ok",
            "value": [line_payload()],
        },
    }


def wire_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
