"""SQLAlchemy 2 declarative base (D-006).

Tüm ORM modelleri için ortak taban sınıfı. Modeller `documentflow.db.models`
içinde tanımlıdır; Alembic `Base.metadata` üzerinden onların şemasına erişir.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Tüm ORM modelleri için ortak declarative taban."""
