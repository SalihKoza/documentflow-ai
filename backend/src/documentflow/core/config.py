"""Merkezi configuration (D-011).

Yalnızca configuration okur; iş mantığı içermez. Değerler ortam
değişkenlerinden veya `.env` dosyasından yüklenir. Gerçek `.env` dosyası Git'e
eklenmez; repoda yalnızca `.env.example` bulunur.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Tek `.env` dosyası proje kökünde bulunur (bkz. `.env.example`). Çalışma
# dizininden bağımsız okunabilmesi için mutlak yol hesaplanır. Dosya yoksa
# Pydantic sessizce varsayılanları kullanır (testler `.env` gerektirmez).
_ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


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


@lru_cache
def get_settings() -> Settings:
    """Ayarları tekil (cache'li) biçimde döndürür."""
    return Settings()
