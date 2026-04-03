## Closed

Completed on 2026-04-03.

Summary:
- Made legacy `settings.connectors` migration startup-only by running it during app lifespan and removing lazy migration from normal connector reads.
- Kept saved connector instances canonical in the `connectors` table and workspace auth policy canonical in `connector_auth_policies`.
- Updated connector lookup paths to use DB-backed helpers directly, and kept `/api/v1/settings` free of a user-editable `connectors` section.
- Added startup coverage for migrating a legacy `settings.connectors` row into the `connectors` table and deleting the legacy row.
- Updated README and AGENTS docs to describe DB-backed connector storage and legacy migration behavior.

Verification:
- `./.venv/bin/pytest -q tests/test_connectors_api.py tests/test_connector_oauth_service.py tests/test_settings_api.py tests/test_startup_lifecycle.py tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py`
- `./scripts/check-policy.sh` repo-specific checks passed before the broader shared precommit suite reached unrelated PostgreSQL session-reset failures.

