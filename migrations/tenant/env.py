"""Alembic environment for the TENANT schema.

One database per tenant — ADR-016. This script is run once per tenant, by
the provisioning path (DATABASE.md 13.5.1) and by the migration fan-out
(DATABASE.md 13.5). It must never be pointed at the control database.

The URL comes from the environment, never from alembic.ini: TRD 12.5 states
that no secret is committed to the repository at any phase.
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

URL_ENV = "GL_TENANT_DB_URL"
VERSION_TABLE = "alembic_version_tenant"


def _url() -> str:
    url = os.environ.get(URL_ENV) or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            f"{URL_ENV} is not set. Tenant migrations are run per tenant "
            f"database; see DATABASE.md 13.5 and the Makefile."
        )
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
        # DATABASE.md 13.5: each tenant migrates in its own transaction, so
        # one tenant's failure never leaves another partially migrated.
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
