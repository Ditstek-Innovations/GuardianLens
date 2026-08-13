"""Alembic environment for the CONTROL schema.

One per installation. Routing, lifecycle and operational state only —
ADR-017. This script must never be pointed at a tenant database, and a
control revision must never be applied to one (DATABASE.md 13.4).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: fileConfig's default disables every
    # logger created before it runs. Provisioning executes this env inside
    # the application process (and inside pytest), and silently disabling
    # other packages' loggers there suppresses alerts they are required
    # to emit. Alembic's own logging is unaffected.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

URL_ENV = "GL_CONTROL_DB_URL"
VERSION_TABLE = "alembic_version_control"


def _url() -> str:
    url = os.environ.get(URL_ENV) or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(f"{URL_ENV} is not set.")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, version_table=VERSION_TABLE)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
