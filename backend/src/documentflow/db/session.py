"""Veritabanı bağlantısı ve oturum yönetimi (D-005, D-006).

Senkron SQLAlchemy 2 engine ve session factory. `create_engine` tembeldir:
gerçek bağlantı ancak ilk kullanımda açılır, bu nedenle bu modülü import etmek
çalışan bir PostgreSQL gerektirmez — çekirdek testler veritabanısız çalışmaya
devam eder. Declarative taban `documentflow.db.base`, modeller
`documentflow.db.models` içindedir.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from documentflow.core.config import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session() -> Iterator[Session]:
    """İstek başına bir veritabanı oturumu sağlar (FastAPI dependency)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
