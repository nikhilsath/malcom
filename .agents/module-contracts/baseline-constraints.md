# Baseline Architecture Constraints (TASK-019)

> Recorded as part of TASK-019 Step 1. This document captures the architecture
> baseline, hotspot files, public API/UI contracts, DB schema ownership, and
> connector source-of-truth flows that must hold as invariants across any
> modularisation work.

---

## Hotspot Files (Large or Mixed-Responsibility)

These files exceed the 600-line heuristic or carry multiple distinct
responsibilities. They are the primary targets for later extraction steps
(Steps 7–14).

| File | Lines | Primary Concern(s) | Notes |
|---|---|---|---|
| `backend/services/helpers.py` | ~5 016 | Catch-all helper/utility functions | Primary extraction target for Steps 7–9 |
| `backend/services/automation_execution.py` | ~3 182 | Automation step execution | Candidate for step-type-specific sub-modules (Step 9) |
| `backend/services/connectors.py` | ~1 467 | Connector lifecycle, secret mgmt, catalog | Split targets: secrets → `connector_secrets.py`, migrations → `connector_migrations.py` (Step 7) |
| `backend/services/apis.py` | ~1 164 | Outgoing and inbound API helpers | Moderate; review before splitting |
| `backend/services/automation_executor.py` | ~990 | Automation executor dispatch | Partially extracted already; Step 9 target |
| `backend/routes/tools.py` | ~448 | Tool CRUD + execution routes | Moderate; review before splitting |
| `backend/routes/log_tables.py` | ~365 | Log table routes | Extract service modules in Step 10 |
| `ui/src/automation/app.tsx` | ~676 | Automation builder orchestrator | Already partially addressed in TASK-017; Step 12 target |
| `ui/src/automation/useAutomationBuilderController.ts` | ~548 | Builder state/logic controller | Step 13 target |
| `ui/src/automation/trigger-settings-form.tsx` | ~381 | Trigger settings form | Step 13 target |

---

## Public API / UI Contracts

### Backend Public Contracts

These endpoints are the canonical API surface. Refactoring must not change
their HTTP method, path, or response shape without a versioned migration.

| Endpoint | Handler module | DB tables touched |
|---|---|---|
| `GET /api/v1/automations/workflow-connectors` | `backend/routes/automations.py` → `backend/services/workflow_builder.py:list_workflow_builder_connectors` | `connectors` |
| `GET /api/v1/connectors/activity-catalog` | `backend/routes/connectors.py` | `connector_endpoint_definitions` |
| `GET /api/v1/connectors/http-presets` | `backend/routes/connectors.py` | `connector_endpoint_definitions` |
| `POST /api/v1/connectors` | `backend/routes/connectors.py` | `connectors` |
| `DELETE /api/v1/connectors/{id}` | `backend/routes/connectors.py` | `connectors` |
| `GET /api/v1/tools` | `backend/routes/tools.py` | `tools` |
| `GET /api/v1/automations` | `backend/routes/automations.py` | `automations`, `automation_steps` |
| `POST /api/v1/automations/{id}/run` | `backend/routes/automations.py` | `automation_runs`, `automation_run_steps` |
| `GET /health` | `backend/routes/runtime.py` | — |

### UI Entry Points

| Page section | Entry file(s) | React or vanilla |
|---|---|---|
| Automation builder | `ui/src/automation/main.tsx` | React |
| Automation overview | `ui/src/automation/overview-main.tsx` | React |
| Dashboard | `ui/src/dashboard/` | React |
| Settings, Connectors | `ui/scripts/settings/`, `ui/scripts/settings/connectors.js` | Vanilla |
| Tools catalog | `ui/scripts/tools/` | Vanilla |

---

## DB Schema Ownership

Canonical DB schema is in `backend/database.py`. The table→owner mapping below
must be kept aligned with `AGENTS.md §Database Schema` and `README.md`.

| Table group | Tables | Primary writer module |
|---|---|---|
| API registry | `inbound_apis`, `inbound_api_events`, `outgoing_scheduled_apis`, `outgoing_continuous_apis`, `webhook_apis`, `webhook_api_events`, `outgoing_delivery_history` | `backend/services/apis.py` |
| Workspace state | `tools`, `tool_configs`, `settings`, `integration_presets`, `connectors`, `connector_auth_policies`, `connector_endpoint_definitions` | `backend/tool_registry.py` (tools), `backend/services/connectors.py` (connectors), `backend/services/helpers.py` (settings/presets) |
| Automation runtime | `automations`, `automation_steps`, `automation_runs`, `automation_run_steps`, `runtime_resource_snapshots` | `backend/routes/automations.py`, `backend/services/automation_executor.py` |
| Script library | `scripts` | `backend/services/scripts.py` |
| Log schema | `log_db_tables`, `log_db_columns` | `backend/routes/log_tables.py` |
| Storage | `storage_locations`, `repo_checkouts` | `backend/services/storage_locations.py` |

---

## Connector Source-of-Truth Flows

These flows must remain intact across all refactor steps:

1. **Saved connector instances**: persisted in `connectors` table; written only by `backend/routes/connectors.py` + `backend/services/connectors.py`; legacy `settings.connectors` rows are read-once startup migration input.
2. **OAuth lifecycle**: token exchange, refresh, and revoke handled exclusively in `backend/services/connector_oauth.py`; route handlers delegate, never implement. (→ R-CONN-005)
3. **Workflow-builder options**: resolved by `backend/services/workflow_builder.py:list_workflow_builder_connectors` → `GET /api/v1/automations/workflow-connectors` → `ui/src/automation/app.tsx`. No parallel availability list allowed. (→ R-CONN-004)
4. **Activity catalog**: sourced from persisted `connector_endpoint_definitions` rows; no code-side catalog at runtime. (→ R-SOT-001)

---

## Refactor Constraints (Locked Invariants)

These conditions must hold **before and after** every extraction in Steps 7–14:

1. All currently passing tests (`python3 -m pytest tests/ -q`) continue to pass.
2. All currently passing UI tests (`cd ui && npm test`) continue to pass.
3. No endpoint path, HTTP method, or response schema changes unless the task explicitly targets it.
4. No DB table name or column name changes unless the task explicitly targets it with a migration.
5. `backend/routes/connectors.py` contains no provider-specific OAuth token lifecycle helper functions. (R-CONN-005)
6. `backend/services/workflow_builder.py:list_workflow_builder_connectors` remains the sole backend resolver for workflow-builder connector options. (R-CONN-004)
7. Seed constants in `backend/tool_registry.py` remain the bootstrap source and do not grow into a parallel runtime registry after DB rows exist. (R-SOT-001)
8. Any new module created during extraction must have an entry in `.agents/module-contracts/` before the PR is merged.

---

## Modularity Acceptance Criteria (Step 2)

These criteria apply to **each module extracted** in Steps 7–14:

### Per-Module Structural Rules

| Criterion | Threshold / Rule |
|---|---|
| Max public API size | ≤ 20 exported symbols per module (functions, classes, or constants) |
| File line count | ≤ 600 lines per source file (policy threshold matches `check-policy.sh`) |
| Inbound dependencies | Listed in the module contract under "Inbound Dependencies" |
| Allowed callers | Explicit allowlist in the module contract under "Allowed Callers" |
| Circular imports | Zero; verified by import-order linting or manual check |

### Per-Module Test Coverage Rules

| Test tier | Requirement |
|---|---|
| Unit tests | All public functions/hooks must have unit tests in `tests/unit/test_<module>.py` or `ui/src/**/__tests__/` |
| Contract tests | All cross-module boundaries must have contract tests in `tests/contract/test_<module>_contract.py` |
| E2E tests (UI only) | Happy-path user flows must be covered in `ui/e2e/<module>.spec.ts` for any new UI component |
| Run command | `scripts/test-module.sh <module-name>` |

### CI Integration Rules

| CI job | Trigger | Command |
|---|---|---|
| `module-<name>-unit` | PR touching `backend/services/<name>.py` or `ui/src/<name>/` | `scripts/test-module.sh <name> --unit` |
| `module-contract-<name>` | PR touching the module or its allowed callers | `scripts/test-module.sh <name> --contract` |

### PR Scope Rules

- Each PR must extract exactly one module concern (single-responsibility change).
- PR title must follow `[module] Extract <concern> from <source-file>` pattern for extraction PRs.
- PR must include the module contract file in `.agents/module-contracts/<name>.md`.
- PR must not change DB schema unless the extraction requires it, and if so, must include a migration.

---

*Last updated: TASK-019 Step 1 & 2*
