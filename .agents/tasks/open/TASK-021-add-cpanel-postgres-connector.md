Note: Follow TASK-019 modularization rules: add a module contract file `.agents/module-contracts/connector_postgres.md` documenting owner, public API, owned DB tables (if any), inbound/outbound dependencies, and test obligations. Include unit + contract tests in the same PR. Verify module-scoped tests via `scripts/test-module.sh connector` where applicable.
Additional completion check: A module contract file `.agents/module-contracts/connector_postgres.md` exists and the new tests run under `scripts/test-module.sh connector` (or appropriate module name) as part of the PR.
Note: The commit must include the module contract and the new/updated tests per TASK-019; CI should be able to run `scripts/test-module.sh connector` to validate the connector tests in isolation.
Execution steps

2. [x] [backend]
Files: backend/services/connectors.py
Action: Add a new connector provider id `cpanel_postgres` to `SUPPORTED_CONNECTOR_PROVIDERS` and add a catalog entry in `DEFAULT_CONNECTOR_CATALOG`. Add a matching provider metadata entry in `DEFAULT_CONNECTOR_PROVIDER_METADATA` describing setup fields: host, port, database, username, password, optional `sslmode`, `auth_types` set to ["basic"], and docs/ui copy. Keep naming consistent with existing provider IDs.
Completion check: `grep -n "cpanel_postgres" backend/services/connectors.py` returns at least one match and the catalog/provider metadata contains the new entry.
Note: Added `backend/services/connector_postgres.py` implementing `probe_postgres_connection` and `_probe_cpanel_postgres_credentials` in `connector_health.py`.
1. [-] [backend]
Files: backend/services/connector_health.py, backend/services/connector_postgres.py (new)
Action: Implement a Postgres connection probe helper. Create `backend/services/connector_postgres.py` exposing `probe_postgres_connection(auth_config: dict[str, Any]) -> tuple[bool, str]` which uses `psycopg` (psycopg[binary]) to attempt a short connection with provided host, port, dbname, user, password and optional sslmode; return `(True, "PostgreSQL connection verified.")` on success and `(False, "<user-facing message>")` or raise `HTTPException` with 502 on network errors similar to other probes. Add a thin wrapper `_probe_cpanel_postgres_credentials` in `connector_health.py` that calls the new helper and normalizes messages.
Completion check: file `backend/services/connector_postgres.py` exists and `connector_health.py` contains `_probe_cpanel_postgres_credentials` or an import referencing `probe_postgres_connection`.

Note: I'll add the provider id, catalog entry, and provider metadata in `backend/services/connectors.py`.
1. [x] [backend]
Files: backend/routes/connectors.py
Action: Wire the new probe into the connector `test` endpoint: import the probe function and add a branch `elif provider == "cpanel_postgres":` that extracts host/port/db/user/password from the `secret_map`/`auth_config` and calls the probe to determine `ok` and `message`, then set `record["status"]` accordingly (connected/needs_attention). Mirror patterns used for `trello`/`notion` tests.
Completion check: `grep -n "cpanel_postgres" backend/routes/connectors.py` returns the new test branch and imports.

Note: Added `cpanel_postgres` to `SUPPORTED_CONNECTOR_PROVIDERS`, inserted a catalog entry in `DEFAULT_CONNECTOR_CATALOG`, and added provider metadata in `DEFAULT_CONNECTOR_PROVIDER_METADATA` with setup fields and UI copy.
Files: tests/test_connectors_cpanel_postgres.py
Action: Add unit tests that create a `cpanel_postgres` connector record via `POST /api/v1/connectors` and assert `POST /api/v1/connectors/{id}/test` behaves as expected. To avoid external dependencies, patch the probe function to return success/failure in the test (use `unittest.mock.patch`), following existing test patterns used for Notion/Trello/GitHub. Keep tests isolated and deterministic.
Completion check: `ls tests | grep test_connectors_cpanel_postgres.py` and the test file imports the connector API and uses patch to simulate probe results.

5. [ ] [docs]
Files: README.md, backend/services/connectors.py (doc strings)
Action: Add a short note in `README.md` and the connector provider catalog comment documenting the new `cpanel_postgres` provider and its setup fields and intended use (connect to cPanel-managed PostgreSQL instances using host/port/db/user/password). Keep wording consistent with existing provider docs.
Completion check: `grep -n "cpanel_postgres" README.md` returns at least one match and provider catalog comment updated.

6. [ ] [github]
Files: backend/services/connectors.py, backend/services/connector_postgres.py, backend/services/connector_health.py, backend/routes/connectors.py, tests/test_connectors_cpanel_postgres.py, README.md, .agents/tasks/open/TASK-021-add-cpanel-postgres-connector.md
Action: When implementation and tests are ready, stage only the modified/added files above, commit with a focused message `Add cPanel PostgreSQL connector provider and health probe`, move this task file from `.agents/tasks/open/` to `.agents/tasks/closed/` in the same commit, and push.
Completion check: `git log -1 --stat` shows the commit message and the listed files; `.agents/tasks/open/TASK-021-...` is no longer present and `.agents/tasks/closed/TASK-021-...` exists.

Test impact review

- tests/test_connectors_api.py: keep; may require small updates if provider-specific metadata expectations are asserted. Recommended action: review tests for hardcoded provider lists and update expectations to include `cpanel_postgres` where appropriate. Validation command: `pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase -q`.

- tests/test_connectors_availability.py: keep; ensure new provider appears in catalog when expected. Validation command: `pytest -q tests/test_connectors_availability.py -q`.

- tests/test_connectors_for_builder.py & tests/test_connectors_for_builder_extra.py: keep; they exercise connectors listing and workflow-builder options. Validation command: `pytest -q tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py -q`.

- tests/test_workflow_builder_service.py: keep; may need no change if builder consumes DB-backed catalog. Validation command: `pytest -q tests/test_workflow_builder_service.py -q`.

- New test file `tests/test_connectors_cpanel_postgres.py`: replace/add — run via `pytest -q tests/test_connectors_cpanel_postgres.py -q`.

Testing steps

1. [ ] [test]
Files: none (testing step)
Action: Run the new unit tests for cPanel Postgres and the connector test endpoint unit tests first:

```
pytest -q tests/test_connectors_cpanel_postgres.py -q
pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase -q
```

Completion check: tests pass locally (exit code 0) and assert that the `/test` endpoint responds with expected JSON when probe is patched.

2. [ ] [test]
Files: none (testing step)
Action: Run connector-related test groups to ensure no regressions:

```
pytest -q tests/test_connectors_availability.py tests/test_connectors_for_builder.py tests/test_workflow_builder_service.py -q
```

Completion check: all specified tests pass.

Documentation review

1. [ ] [docs]
Files: README.md
Action: Add a short provider entry explaining `cpanel_postgres` provider usage and required setup fields. Also update `backend/services/connectors.py` provider metadata comment if helpful.
Completion check: README contains `cpanel_postgres` and a one-line description.

GitHub update

1. [ ] [github]
Files: backend/services/connectors.py, backend/services/connector_postgres.py, backend/services/connector_health.py, backend/routes/connectors.py, tests/test_connectors_cpanel_postgres.py, README.md, .agents/tasks/open/TASK-021-add-cpanel-postgres-connector.md
Action: Stage the changed/added files, commit with message: "Add cPanel PostgreSQL connector provider and health probe", move this task file to `.agents/tasks/closed/` in the same commit, and push to origin.
Completion check: remote branch contains the commit and `.agents/tasks/closed/TASK-021-add-cpanel-postgres-connector.md` exists.

Notes/assumptions

- The repo already depends on `psycopg[binary]` per `requirements.txt` so no new dependency changes should be required.
- Implementation will follow existing connector patterns for auth field naming (use `host`, `port`, `database`, `username`, `password` or `db` naming consistent with other code; prefer `database` for clarity).
- Tests will patch the probe to avoid requiring an actual cPanel-hosted Postgres instance.
- If desired, a future step could add interactive UI wiring for cPanel Postgres provider setup in the frontend; this task focuses on backend/provider plumbing and tests.
