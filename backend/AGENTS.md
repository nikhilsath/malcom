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

The schema source of truth is `backend/database.py`, not any checked-in database file.

Use the live database to inspect current state.
Use `backend/database.py` to change structure.

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
2. add new `CREATE TABLE IF NOT EXISTS` definitions there if introducing a table
3. use `_ensure_column(...)` for additive column changes to existing tables
4. keep booleans as integer-compatible values (`0`/`1`) for cross-database compatibility
5. keep structured payloads in `*_json` text columns unless there is a strong reason not to
6. update API serialization/deserialization logic and tests in the same task

Agents must not:

- treat any runtime DB file as the schema source of truth
- hand-edit runtime database tables/columns directly as a substitute for code changes
- create ad hoc migration files unless the repo adopts a formal migration system first

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

### Workflow storage files

- Workflow storage files are stored under the configured `data.workflow_storage_path` (default: `backend/data/workflows`).
- Service code that implements file-backed storage should live in `backend/services/` and avoid importing higher-level runtime modules to prevent circular import issues.
- Any change to storage behavior that affects runtime contracts must include unit tests and be documented in `AGENTS.md`.

Example write-step (YAML):

```yaml
- type: log
  storage_type: csv
  storage_target: events
  storage_new_file: false
  payload:
    - ts
    - event
    - value
```

Implementation notes:
- Keep storage helper functions under `backend/services/workflow_storage.py` or similar and ensure they use atomic temp-file+rename semantics.
- Default storage path is `data.workflow_storage_path` (configured in app settings); do not hardcode absolute paths.

---

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
