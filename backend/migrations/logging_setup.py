from __future__ import annotations

from logging.config import fileConfig


def configure_alembic_logging(config_file_name: str | None) -> None:
    if config_file_name is None:
        return

    # Preserve existing app/server loggers so Alembic startup output does not
    # silence Uvicorn lifecycle logs during runtime bootstrapping.
    fileConfig(config_file_name, disable_existing_loggers=False)
