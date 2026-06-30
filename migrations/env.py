from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # noqa: F401
from app.config import DATABASE_URL
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure(connection=None, url: str | None = None) -> None:
    options = {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
    }
    if connection is not None:
        options["connection"] = connection
        options["render_as_batch"] = connection.dialect.name == "sqlite"
    else:
        options["url"] = url
        options["literal_binds"] = True
        options["dialect_opts"] = {"paramstyle": "named"}
    context.configure(**options)


def run_migrations_offline() -> None:
    _configure(url=DATABASE_URL)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
