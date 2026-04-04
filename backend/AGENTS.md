# backend/AGENTS.md

Root policy remains authoritative in AGENTS.md.
This file defines backend-domain implementation rules and should be read after root routing.

## Scope

Applies to backend implementation, schema, API route behavior, connector/tool backend wiring, and backend-side verification expectations.

---

## Repo Map (Backend)

- `backend/main.py`
  - FastAPI app factory
  - router registration
  - static mounts for built assets and raw shell scripts/styles
- `backend/routes/api.py`
  - JSON API endpoints
- `backend/routes/ui.py`
  - HTML page routes and redirect routes
  - this is the source of truth for served UI URLs
- `backend/database.py`
  - database connection helpers
  - schema initialization
  - additive schema evolution via `_ensure_column`
- `backend/tool_registry.py`
  - default tool catalog
  - tool manifest generation
  - tool database sync logic
- `backend/services/`
  - backend business logic and service helpers
- `backend/schemas.py`
  - Pydantic request/response models
- `backend/data/logs/`
  - application log output

---

## Database Structure

### Source Of Truth

The repo-facing schema structure source of truth is `backend/database.py`.
Alembic migrations under `backend/migrations/` are the required structural change log and execution path, and they must stay aligned with `backend/database.py`.

Use the live database to inspect current state.
Use Alembic migrations to change structure.
Do not treat the live database as an editable source of truth.

### Database Location

- runtime DB: PostgreSQL (`MALCOM_DATABASE_URL`)
- connection helper: `backend/database.py:connect`
- initialization entrypoint: `backend/database.py:initialize`

### Table Groups

#### API Registry Tables

- `inbound_apis`
  - inbound API definitions
  - includes auth type, secret hash, enablement, mock flag, timestamps
- `inbound_api_events`
  - inbound request/event history tied to `inbound_apis`
- `outgoing_scheduled_apis`
  - scheduled outbound deliveries
  - includes URL, auth config JSON, payload template, schedule, run timestamps
- `outgoing_continuous_apis`
  - continuous/repeating outbound deliveries
- `webhook_apis`
  - webhook publisher definitions and verification settings

#### Tool Directory

- `tools`
  - persisted tool metadata
  - stores seed metadata plus overrides and enablement
  - frontend tool catalog and sidenav derive from this flow

#### Workspace Settings

- `settings`
  - JSON settings payloads keyed by setting name
- `integration_presets`
  - provider catalog defaults and metadata
- `connectors`
  - saved connector instance rows and protected auth state
  - canonical runtime source of truth for saved connector instances; legacy `settings.connectors` rows are startup-migration input only
- `connector_auth_policies`
  - workspace-level connector credential policy row
- `connector_endpoint_definitions`
  - persisted connector activity and HTTP preset catalog rows

#### Automation Tables

- `automations`
  - automation definitions and trigger configuration
- `automation_steps`
  - ordered steps for an automation
- `automation_runs`
  - execution history for automations
- `automation_run_steps`
  - per-step execution history for each run

#### Script Library

- `scripts`
  - stored script definitions
  - includes code, language, validation state, timestamps

### Schema Rules

When changing the DB schema, agents must:

1. update `backend/database.py`
2. add a new migration under `backend/migrations/versions/` for table/column changes
3. keep `backend/database.py:run_migrations()` and initialization flow aligned with migration ownership
4. keep booleans as integer-compatible values (`0`/`1`) for cross-database compatibility
5. keep structured payloads in `*_json` text columns unless there is a strong reason not to
6. update API serialization/deserialization logic and tests in the same task

Agents must not:

- treat any runtime DB file as the schema source of truth
- hand-edit runtime database tables/columns directly as a substitute for code changes
- bypass migration files for structural schema changes

## Backend Service Factoring And Canonical Fixes

1. Keep provider-specific, connector-specific, or integration-specific behavior in scoped service modules (for example `backend/services/connector_<provider>*.py`) instead of growing generic route or service files with more branches.
2. When a backend file is already carrying multiple responsibilities, extract the new concern into an adjacent helper or service before adding more conditionals to the largest file in the area.
3. Fix the canonical backend resolver or write path rather than adding fallback reads from settings payloads, duplicated constants, or second-chance route logic.
4. For DB-backed connector, activity, preset, and catalog state, persist and resolve through DB-backed services and routes; code constants may seed defaults but must not become a second runtime registry.

---

## File Placement Rules (Backend)

### Backend Files

Place new backend files by responsibility:

- routes: `backend/routes/<feature>.py`
- service/business logic: `backend/services/<feature>.py`
- schema/model changes: `backend/schemas.py`
- DB helpers and schema: `backend/database.py`
- app wiring and mounts: `backend/main.py`
- UI route wiring and redirects: `backend/routes/ui.py`
- tests: `tests/test_<feature>.py`

Backend rules:

- do not put business logic directly in HTML routes unless it is route-only glue
- do not put SQL in frontend files
- do not add served HTML routes in `backend/main.py`; add them in `backend/routes/ui.py`

---

### Connector OAuth Notes

Trello now supports guided OAuth onboarding in the connector flow. You can configure Trello client credentials in the setup form or provide the following environment variables to avoid entering them interactively:

- `MALCOM_TRELLO_OAUTH_CLIENT_ID` — Trello app API key / client id.
- `MALCOM_TRELLO_OAUTH_CLIENT_SECRET` — Trello app client secret (optional depending on Trello app configuration).

Default Trello OAuth callback path: `/api/v1/connectors/trello/oauth/callback`.

Note: Trello's current onboarding contract does not provide long-lived refresh tokens; the connector flow treats Trello as an access-token-only provider and refresh attempts will return `409` with a suitable message.


## Tool Input/Output Contract

Every tool in the catalog that can be used as a workflow step must declare its input and output fields. These fields drive:
- DB sync (stored in `inputs_schema_json` and `outputs_schema_json` on the `tools` table)
- Frontend tool manifest (`ui/scripts/tools-manifest.js`) for dynamic form rendering in the automation canvas
- Backend validation in `validate_automation_definition()`
- Execution engine dispatch and `inputs_json` tracking in `automation_run_steps`

### Field Descriptor Format

Each entry in `inputs` and `outputs` is a dict with:

```python
{
    "key": "text",          # machine-readable key, used in tool_inputs dict and template vars
    "label": "Text to Speak",  # human-readable label shown in the workflow canvas
    "type": "text",         # string | text | number | select
    "required": True,       # inputs only; omit or False for optional
    "options": ["a", "b"],  # select type only
}
```

### Supported Types

- `string` — single-line text input
- `text` — multiline textarea
- `number` — numeric input
- `select` — dropdown; requires `options` list

### Adding a New Tool with I/O Contract

1. Add the tool to `DEFAULT_TOOL_CATALOG` in `backend/tool_registry.py` with `inputs` and `outputs` lists
2. Add the execution handler in `backend/services/support.py`:
   - Read inputs via `_get_tool_input(step, "key", context)`
   - Return `RuntimeExecutionResult` with `output` as a dict keyed by output field keys
   - Add dispatch in `execute_automation_step()` tool handler
3. Add required-input validation in `validate_automation_definition()`
4. Run `node scripts/generate-tools-manifest.mjs` and `npm run build` in `ui/`

### Tool Step Contract

Workflow tool step contract:

- `type` must be `"tool"`
- `tool_id` must match a catalog id
- inputs are stored in `config.tool_inputs: { key: value }`
- downstream outputs are addressed as `{{steps.<step_name>.<output_key>}}`

### Policy

Only add tools to the catalog when:
- A backend execution handler is designed and implemented
- Input/output schemas are defined
- The tool page (`ui/tools/<id>.html`) and script (`ui/scripts/tools/<id>.js`) exist

Do not add placeholder tools. Remove tools from the catalog if their execution backend is removed.

### Currently Implemented Tools

| Tool ID | Inputs | Key Outputs |
|---------|--------|-------------|
| `coqui-tts` | text (req), output_filename, speaker, language | `audio_file_path` |
| `llm-deepl` | user_prompt (req), system_prompt, model_identifier | `response_text`, `model_used` |
| `smtp` | relay_host (req), relay_port (req), from_address (req), to (req), subject (req), body (req), relay_security, relay_username, relay_password | `status`, `message` |

---

## Tool Registration Requirements

Tools are registered by backend catalog plus database sync, not by static frontend markup and not by per-tool JSON files.

### Source Of Truth

- `backend/tool_registry.py`
  - default tool catalog seed data
  - tool metadata validation
  - sync into the runtime database
- `tools` table in PostgreSQL
  - persisted tool state, enablement, overrides
- `ui/scripts/tools-manifest.js`
  - generated frontend manifest
- `scripts/generate-tools-manifest.mjs`
  - manifest generation script

### Required Metadata Fields

- `id`
- `name`
- `description`

Validation rules:

- every registered tool must have a backend catalog entry
- all required fields must be non-empty strings
- `id` values must remain stable because they map to DB rows, routes, pages, and sidenav items

### Tool Folder Rules

The top-level `tools/` folder is not a registration source.

- use `tools/<tool-id>/` only for non-app collateral if needed
- do not create `tools/<tool-id>/tool.json` as a registration source
- do not move frontend page logic there
- do not move primary backend route/service logic there
- primary app code remains in `backend/` and `ui/`

### Tool Change Workflow

When adding or changing tools, agents must:

1. create or update the tool catalog entry in `backend/tool_registry.py`
2. run `node scripts/generate-tools-manifest.mjs`
3. verify that `ui/scripts/tools-manifest.js` changed as expected
4. add or update `ui/tools/<tool-id>.html`
5. add or update `ui/scripts/tools/<tool-id>.js`
6. add the page to `ui/vite.config.ts`
7. add the served HTML route in `backend/routes/ui.py`
8. verify that `ui/tools/catalog.html` reflects the tool without manual card markup changes
9. verify that the tools sidenav updates through the shared config/manifest flow

Agents must not:

- hardcode new tools directly into `ui/tools/catalog.html`
- hardcode new tools directly into `ui/scripts/tools.js`
- manually hardcode tool sidenav links on individual pages
- add `tools/<tool-id>/tool.json` files for registration

---

## Generated And Runtime Files

Agents must not hand-edit generated or runtime artifact files unless the task explicitly targets them:

- `ui/dist/**`
- `ui/scripts/tools-manifest.js` without also regenerating it from the script
- runtime database objects directly as a substitute for schema/code changes
- `ui/node_modules/**`
- `node_modules/**`

If a generated file is expected to change, regenerate it from its source workflow and mention that in verification.
