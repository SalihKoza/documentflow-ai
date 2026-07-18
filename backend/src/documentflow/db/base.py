"""SQLAlchemy 2 declarative base (D-006).

Tüm ORM modelleri için ortak taban sınıfı. Bu aşamada bağlı bir model/tablo
yoktur; modeller ilgili geliştirme aşamalarında eklenecektir. Alembic,
`Base.metadata` üzerinden gelecekteki modellerin şemasına erişir.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Tüm ORM modelleri için ortak declarative taban."""
