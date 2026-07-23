"""Alembic ortam betiği (senkron — D-006).

Veritabanı URL'i uygulama Settings'inden (D-011) okunur; alembic.ini içinde
gizli bilgi tutulmaz. `target_metadata`, uygulama Base'inin metadata'sına
bağlanır.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from documentflow.core.config import get_settings

# Modellerin import edilmesi ZORUNLUDUR: aksi hâlde `Base.metadata` boş kalır ve
# autogenerate/check tüm tabloları "silinmiş" sanır.
from documentflow.db import models  # noqa: F401  (yan etki için import)
from documentflow.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL'i ortamdan/Settings'ten al (alembic.ini'de saklanmaz).
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """URL kullanarak 'offline' modda migration çalıştırır."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Bir Engine oluşturup 'online' modda migration çalıştırır."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
