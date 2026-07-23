"""Merkezi configuration (D-011).

Yalnızca configuration okur; iş mantığı içermez. Değerler ortam
değişkenlerinden veya `.env` dosyasından yüklenir. Gerçek `.env` dosyası Git'e
eklenmez; repoda yalnızca `.env.example` bulunur.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Proje kökü: `backend/src/documentflow/core/config.py` -> dört üst dizin.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Tek `.env` dosyası proje kökünde bulunur (bkz. `.env.example`). Çalışma
# dizininden bağımsız okunabilmesi için mutlak yol hesaplanır. Dosya yoksa
# Pydantic sessizce varsayılanları kullanır (testler `.env` gerektirmez).
_ROOT_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Uygulama ayarları."""

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://documentflow:documentflow_local@localhost:5432/documentflow"
    )

    # Yüklenen PDF'lerin saklandığı kök (D-047: dosya sistemi + DB'de yol).
    # Varsayılan olarak `data/private/` altındadır; orası `.gitignore` ile
    # dışlanmıştır, böylece gerçek belgeler kazara repoya giremez.
    storage_root: Path = _PROJECT_ROOT / "data" / "private" / "documents"

    # Extraction sağlayıcısı. Model kararı henüz verilmediğinden (D-049) tek
    # desteklenen değer `recorded`: kaydedilmiş bir yanıt döndürür, gerçek
    # çıkarım YAPMAZ. Gerçek adapter eklendiğinde burası genişletilir.
    extraction_provider: str = "recorded"
    # Kaydedilmiş yanıt dosyası. Verilmezse yerleşik sentetik demo yanıtı
    # kullanılır (bkz. `documentflow.api.deps`).
    recorded_response_path: Path | None = None


@lru_cache
def get_settings() -> Settings:
    """Ayarları tekil (cache'li) biçimde döndürür."""
    return Settings()
