from __future__ import annotations

import unittest
from unittest import mock

from backend.migrations.logging_setup import configure_alembic_logging


class AlembicLoggingSetupTestCase(unittest.TestCase):
    def test_configure_alembic_logging_preserves_existing_loggers(self) -> None:
        with mock.patch("backend.migrations.logging_setup.fileConfig") as file_config_mock:
            configure_alembic_logging("data/config/alembic.ini")

        file_config_mock.assert_called_once_with("data/config/alembic.ini", disable_existing_loggers=False)

    def test_configure_alembic_logging_skips_missing_config(self) -> None:
        with mock.patch("backend.migrations.logging_setup.fileConfig") as file_config_mock:
            configure_alembic_logging(None)

        file_config_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
