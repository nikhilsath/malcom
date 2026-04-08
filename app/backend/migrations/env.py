from __future__ import annotations

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.database import get_database_url
from backend.migrations.logging_setup import configure_alembic_logging

config = context.config

# Fix config_file_name to point to the correct alembic.ini location
config_file_name = config.config_file_name
if config_file_name and not os.path.isabs(config_file_name):
    # When running migrations from app/, we need to find the correct alembic.ini
    # Check workspace root first
    workspace_root = Path(__file__).resolve().parents[3]
    
    # Try different possible locations
    possible_paths = [
        workspace_root / config_file_name,  # workspace_root/data/config/alembic.ini
        workspace_root / "data" / "config" / "alembic.ini",  # Try absolute data config path
    ]
    
    for possible_path in possible_paths:
        if possible_path.exists():
            config_file_name = str(possible_path)
            break

# Fix script_location to be relative to workspace root instead of current directory
if config.get_main_option("sqlalchemy.url") is not None:
    # When running migrations, we need to ensure script_location points to the right place
    script_location = config.get_main_option("script_location")
    if script_location and not os.path.isabs(script_location):
        # Get workspace root by going up from this file's directory
        workspace_root = Path(__file__).resolve().parents[3]
        correct_script_location = workspace_root / script_location
        if correct_script_location.exists():
            config.set_main_option("script_location", str(correct_script_location))

configure_alembic_logging(config_file_name)

target_metadata = None


def _resolve_database_url() -> str:
    configured_url = (config.get_main_option("sqlalchemy.url") or "").strip()
    if configured_url:
        return configured_url
    return get_database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_database_url()

    connectable = engine_from_config(
        section,
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
