"""API katmanı bağımlılıkları (FastAPI dependency'leri).

Extraction sağlayıcısı buradan enjekte edilir. Model kararı henüz verilmediği
için (D-049) tek desteklenen sağlayıcı `recorded`'dır: kaydedilmiş bir yanıt
döndürür ve **gerçek çıkarım yapmaz**. Bu durum review ekranında görünür bir
uyarı olarak gösterilir; kullanıcıya gerçek çıkarım yapıldığı izlenimi verilmez.
"""

import json
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from documentflow.core.config import Settings, get_settings
from documentflow.db.session import get_session
from documentflow.extraction import ExtractorProtocol, ProviderMetadata, RecordedExtractor

DEMO_PROVIDER = "recorded"


def _demo_field(value: str, raw: str | None = None) -> dict[str, Any]:
    return {"raw": raw if raw is not None else value, "value": value, "status": "ok"}


def _demo_response() -> str:
    """Yerleşik sentetik demo yanıtı.

    Tamamen uydurmadır; gerçek bir belgeden türetilmemiştir ve yüklenen PDF ne
    olursa olsun AYNI faturayı döndürür. İki bilinçli sorun içerir, böylece
    review ekranı hem `blocking` hem `review` sinyalini gösterir:

    - `fatura_no` kâğıt fatura biçiminde  -> FNO-001 (warning)
    - `genel_toplam` 3.599,00 iken 3.000,00 + 600,00 = 3.600,00 -> ARITH-001 (error)
    """
    payload = {
        "schema_version": "0.1",
        "header": {
            "fatura_no": _demo_field("A-2025/000123"),
            "fatura_tarihi": _demo_field("15.03.2025"),
            "satici_unvan": _demo_field("Ornek Bilisim Ltd. Sti."),
            "satici_vkn": _demo_field("1234567890"),
            "alici_unvan": _demo_field("Ornek Ticaret A.S."),
            "alici_vkn_tckn": _demo_field("9876543217"),
            "ara_toplam": _demo_field("3.000,00"),
            "kdv_toplam": _demo_field("600,00"),
            "genel_toplam": _demo_field("3.599,00"),
        },
        "kalemler": {
            "raw": "Danismanlik Hizmeti 2 1.500,00 %20 3.000,00",
            "status": "ok",
            "value": [
                {
                    "aciklama": _demo_field("Danismanlik Hizmeti"),
                    "miktar": _demo_field("2"),
                    "birim_fiyat": _demo_field("1.500,00"),
                    "kdv_orani": _demo_field("20", "%20"),
                    "satir_tutari": _demo_field("3.000,00"),
                }
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False)


@lru_cache
def _recorded_response_text(path: Path | None) -> str:
    if path is None:
        return _demo_response()
    return path.read_text(encoding="utf-8")


def get_db(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[Session]:
    """İstek başına veritabanı oturumu."""
    del settings
    yield from get_session()


def get_storage_root(settings: Annotated[Settings, Depends(get_settings)]) -> Path:
    return settings.storage_root


def get_extractor(settings: Annotated[Settings, Depends(get_settings)]) -> ExtractorProtocol:
    """Yapılandırılmış extractor'ı döndürür.

    Bilinmeyen bir sağlayıcı adı sessizce yok sayılmaz; açık bir hata verir.
    """
    if settings.extraction_provider != DEMO_PROVIDER:
        raise ValueError(
            f"desteklenmeyen extraction_provider: {settings.extraction_provider!r} "
            f"(su an yalnizca {DEMO_PROVIDER!r} destekleniyor)"
        )
    return RecordedExtractor(
        _recorded_response_text(settings.recorded_response_path),
        metadata=ProviderMetadata(
            provider=DEMO_PROVIDER,
            model="none",
            prompt_version="none",
        ),
    )


def is_demo_extractor(settings: Settings) -> bool:
    """Review ekranındaki uyarıyı sürer."""
    return settings.extraction_provider == DEMO_PROVIDER


SessionDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
StorageRootDep = Annotated[Path, Depends(get_storage_root)]
ExtractorDep = Annotated[ExtractorProtocol, Depends(get_extractor)]
