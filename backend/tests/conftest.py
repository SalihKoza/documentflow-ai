"""Veritabanı gerektiren testler için ortak fixture'lar.

Çekirdek testler (schema, parsing, validation, extraction, flagging) bu
fixture'ları KULLANMAZ ve veritabanısız çalışmaya devam eder. Buradaki
fixture'lar yalnızca `tests/db`, `tests/workflow` ve `tests/api` altında
istenir; PostgreSQL erişilebilir değilse o testler atlanır.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from documentflow.core.config import get_settings

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Migration'ları uygulanmış canlı bir PostgreSQL engine'i.

    Veritabanı erişilemezse tüm DB testleri atlanır (çekirdek suite yeşil kalır).
    Şema `alembic upgrade head` ile kurulur — böylece migration'ın kendisi de
    her koşuda sınanmış olur.
    """
    url = get_settings().database_url
    # Kisa connect_timeout: veritabani yoksa suite saniyeler icinde atlanmali,
    # isletim sisteminin TCP zaman asimini beklememeli.
    candidate = create_engine(
        url, pool_pre_ping=True, future=True, connect_args={"connect_timeout": 3}
    )
    try:
        with candidate.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - baglanti kurulamadi, DB testleri atlanir
        candidate.dispose()
        pytest.skip(f"PostgreSQL erisilemez, DB testleri atlandi: {type(exc).__name__}")

    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    yield candidate
    candidate.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Test başına dış bir transaction'a bağlı oturum.

    `join_transaction_mode="create_savepoint"` sayesinde uygulama kodu
    `commit()` çağırsa bile veriler dış transaction geri alındığında yok olur;
    testler birbirini kirletmez.
    """
    connection = engine.connect()
    transaction = connection.begin()
    db_session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    """İzole belge saklama kökü (gerçek `data/private/` hiç kullanılmaz)."""
    root = tmp_path / "documents"
    root.mkdir()
    return root
