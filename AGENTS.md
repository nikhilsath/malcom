# AGENTS.md

## Purpose

Agents work best in this repo when they follow the real architecture instead of inventing parallel structure.

Malcom is a FastAPI application with:

- a PostgreSQL runtime database
- server-rendered HTML entry pages built by Vite
- a mix of React pages and vanilla JavaScript pages
- database-backed tool metadata, settings, scripts, and automation state

This file is the operating manual for future agent changes.

---

## Machine-Readable Policy

### Required Workflow {#required-workflow}

1. Execute work in small, testable steps.
2. Validate each step before moving to the next.
3. Log intermediate outcomes when a task has multiple stages.
4. Include testing instructions whenever code or behavior changes.
5. Match existing repo structure before introducing a new pattern.
6. Prefer extending the current source of truth over creating a second one.

### GitHub Update Workflow {#github-update-workflow}

When the user says to "update github", agents must use this git workflow:

1. run `git add .`
2. run `git commit -m "<logical, task-specific message>"`
3. run `git push`

Rules:

- do not use an empty or generic commit message
- choose a concise commit message that reflects the actual change
- do not run `git push` before `git commit`, because the new changes would not be included

### Required Output For Development Work {#required-output-for-development-work}

Every development-oriented response must include:

- testing instructions
- expected behavior
- verification steps

### Maintenance Sync Rule {#maintenance-sync-rule}

When updating policy, agents must update all of the following in the same change when applicable:

1. canonical prose rules
2. `Quick Task → Where to Edit` reference table
3. `Rules Matrix` entries
4. machine index block between `MACHINE_INDEX_START` and `MACHINE_INDEX_END`

Do not leave machine reference content stale after changing source rules.

---

## Machine Reference Index {#machine-reference-index}

Use this section as the first lookup for task routing. It accelerates file targeting but does not replace canonical rule text below.

### Quick Task → Where to Edit {#quick-task-where-to-edit}

| Task | Primary Files | Also Check | Must Not Edit |
|---|---|---|---|
| Add backend API route | `backend/routes/api.py` | `backend/schemas/`, `tests/test_<feature>.py` | `ui/dist/**` |
| Add served UI page route | `backend/routes/ui.py` | `ui/vite.config.ts`, `ui/<section>/<page>.html` | `backend/main.py` (for UI routes) |
| Change DB schema | `backend/database.py` | related serializers + tests | runtime database objects directly |
| Add or update tool registration | `backend/tool_registry.py` | `backend/services/support.py`, `scripts/generate-tools-manifest.mjs`, `ui/tools/<id>.html`, `ui/scripts/tools/<id>.js`, `ui/vite.config.ts`, `backend/routes/ui.py` | hardcoded tool cards/nav links |
| Add vanilla page logic | `ui/scripts/<section>/<page>.js` | matching HTML + styles in `ui/styles/pages/` | new root-level page entry in `ui/scripts/*.js` |
| Add React page logic | `ui/src/<feature>/` | matching HTML entry + tests | unrelated section folders |
| Update shared shell navigation | `ui/scripts/shell-config.js` | `ui/scripts/navigation.js`, shell page attributes | page-local duplicated topnav/sidenav markup |
| Change generated tool manifest | `scripts/generate-tools-manifest.mjs` | regenerate `ui/scripts/tools-manifest.js` | hand-edit `ui/scripts/tools-manifest.js` without regeneration |

### Rules Matrix {#rules-matrix}

| Rule ID | Requirement | Enforced In |
|---|---|---|
| R-DB-001 | Schema source of truth is `backend/database.py` | Database changes |
| R-UI-001 | Served HTML routes are registered in `backend/routes/ui.py` | UI route wiring |
| R-UI-002 | Explanatory UI descriptions use info-badge pattern | UI pages |
| R-TOOL-001 | Tool registration flows through backend catalog + DB sync | Tool lifecycle changes |
| R-TOOL-002 | Tool page wiring includes Vite input + UI route + page script | Tool page additions |
| R-GEN-001 | Do not hand-edit generated artifacts like `ui/dist/**` | Build outputs |
| R-GEN-002 | Regenerate `ui/scripts/tools-manifest.js` from script source | Tool catalog manifest updates |
| R-TEST-001 | Development work responses include test instructions, expected behavior, and verification steps | All implementation responses |

<!-- MACHINE_INDEX_START
{
  "version": 1,
  "primary_sources": {
    "ui_html_routes": ["backend/routes/ui.py"],
    "db_schema": ["backend/database.py"],
    "tool_catalog": ["backend/tool_registry.py"],
    "tool_manifest_generator": ["scripts/generate-tools-manifest.mjs"],
    "shared_shell": ["ui/scripts/shell-config.js", "ui/scripts/navigation.js"]
  },
  "task_routes": {
    "db_schema_change": {
      "edit": ["backend/database.py"],
      "verify": ["tests/"]
    },
    "new_ui_page": {
      "edit": ["ui/<section>/<page>.html", "ui/vite.config.ts", "backend/routes/ui.py"],
      "verify": ["ui/dist/"]
    },
    "tool_change": {
      "edit": [
        "backend/tool_registry.py",
        "backend/services/support.py",
        "ui/tools/<id>.html",
        "ui/scripts/tools/<id>.js",
        "ui/vite.config.ts",
        "backend/routes/ui.py"
      ],
      "generate": ["scripts/generate-tools-manifest.mjs"],
      "verify": ["ui/scripts/tools-manifest.js", "ui/tools/catalog.html"]
    }
  },
  "forbidden_paths": [
    "ui/dist/**",
    "ui/node_modules/**",
    "node_modules/**"
  ],
  "response_requirements": [
    "testing_instructions",
    "expected_behavior",
    "verification_steps"
  ]
}
MACHINE_INDEX_END -->

---

## Repo Map {#repo-map}

### Backend {#repo-map-backend}

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

### Frontend {#repo-map-frontend}

- `ui/<section>/<page>.html`
  - HTML entry pages
- `ui/src/`
  - React/TypeScript application entrypoints and components
- `ui/scripts/`
  - vanilla JavaScript controllers and shared shell/runtime helpers
- `ui/styles/`
  - shared and page-level CSS
- `ui/assets/`
  - source assets consumed by Vite imports
- `ui/dist/`
  - generated build output
  - do not hand edit

### Other {#repo-map-other}

- `scripts/`
  - developer and maintenance scripts
- `tests/`
  - backend/API tests
- `tools/`
  - reserved for tool-owned collateral if needed later
  - not a registration source of truth
- `media/`
  - repo-level reference media only, not bundled frontend assets

---

## Database Structure {#database-structure}

### Source Of Truth {#database-source-of-truth}

The schema source of truth is `backend/database.py`, not any checked-in database file.

Use the live database to inspect current state.
Use `backend/database.py` to change structure.

### Database Location {#database-location}

- runtime DB: PostgreSQL (`MALCOM_DATABASE_URL`)
- connection helper: `backend/database.py:connect`
- initialization entrypoint: `backend/database.py:initialize`

### Table Groups {#table-groups}

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

### Schema Rules {#schema-rules}

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

## File Placement Rules {#file-placement-rules}

### Backend Files {#backend-files}

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

### Frontend Entry Rules {#frontend-entry-rules}

The repo uses two frontend entry styles.

#### React Pages

React pages mount from `ui/src/`.

Current examples:

- `ui/dashboard/home.html` -> `ui/src/dashboard/main.tsx`
- `ui/dashboard/devices.html` -> `ui/src/dashboard/main.tsx`
- `ui/dashboard/logs.html` -> `ui/src/dashboard/main.tsx`
- `ui/automations/overview.html` -> `ui/src/automation/main.tsx`
- `ui/scripts/library.html` -> `ui/src/scripts-library/main.ts`

Rule:

- if a page is React-driven, its HTML must load a `ui/src/<feature>/main.tsx` or `main.ts` entry
- React components and tests stay under that same `ui/src/<feature>/` tree

#### Vanilla Pages

Vanilla pages must use page-specific entry files under `ui/scripts/<section>/`.

Rule:

- `ui/<section>/<page>.html` must load `ui/scripts/<section>/<page>.js`
- page-specific DOM bindings, listeners, and page orchestration belong in that page module or modules under the same folder
- shared code for a section belongs under the same section folder, not in a new random root-level script

Examples:

- `ui/apis/outgoing.html` -> `ui/scripts/apis/outgoing.js`
- `ui/settings/workspace.html` -> `ui/scripts/settings/workspace.js`
- `ui/tools/llm-deepl.html` -> `ui/scripts/tools/llm-deepl.js`

Legacy note:

- existing root-level files such as `ui/scripts/settings.js`, `ui/scripts/tool-config.js`, `ui/scripts/local-llm.js`, and `ui/scripts/tools.js` are shared controllers from the earlier structure
- agents may import them from page-specific entry files
- agents must not add new page entry files at the root of `ui/scripts/`

### Shared Shell Requirements {#shared-shell-requirements}

Navigation and brand markup are registered by shared shell convention, not by page-local copy/paste.

Required shell sources:

- `ui/scripts/shell-config.js`
- `ui/scripts/navigation.js`

When adding or changing UI pages that use the shell, agents must:

1. update shared navigation or brand definitions in `ui/scripts/shell-config.js` when shell navigation changes
2. use `data-section`, `data-sidenav-item`, and `data-shell-path-prefix` on shell pages
3. render shell placeholders with `id="topnav"` and `id="sidenav"`
4. keep the Malcom brand in the shared shell, not page-local markup
5. avoid duplicating nav labels or hrefs inside individual pages

Agents must not hardcode new topnav or sidenav markup into page HTML when the shared shell applies.

### UI Requirements {#ui-requirements}

For UI-facing work:

- every rendered structural or interactive element must have a stable, deterministic `id`
- CSS classes must be semantic and purpose-based
- utility-first or presentation-only class naming should be avoided

### Info Badge Pattern For Explanatory Text {#info-badge-pattern-for-explanatory-text}

Explanatory descriptions are hidden by default behind info badges. Titles remain visible; explanations are revealed on demand.

**Rule:** Do not render explanatory text as visible paragraphs in the default page state. Instead, place descriptions behind an `.info-badge` toggle button that exposes an `.info-badge-content` panel when clicked.

**Page-level description pattern:**

```html
<div class="page-header section-header--page" id="...">
    <div class="title-row">
        <h2 class="page-title section-header__title--page" id="page-title">Page Title</h2>
        <button type="button" id="page-info-badge" class="info-badge" aria-label="Page information" aria-expanded="false" aria-controls="page-description">i</button>
    </div>
    <p class="page-description section-header__description--page" id="page-description" hidden>Description text.</p>
</div>
```

**Section-level description pattern:**

```html
<div class="title-row">
    <h3 id="section-title">Section title</h3>
    <button type="button" id="section-description-badge" class="info-badge" aria-label="More information" aria-expanded="false" aria-controls="section-description">i</button>
</div>
<p id="section-description" class="section-header__description" hidden>Description text.</p>
```

**CSS classes:**

- `.info-badge` — circular `i` button (20 × 20 px, purple tones); defined in `ui/styles/components.css`
- `.title-row` — flex row for title + badge alignment; defined in `ui/styles/base.css`

**JavaScript:** Toggle behavior is handled globally by `initInfoBadges()` in `ui/scripts/navigation.js`, which runs on every shell page. No per-page wiring is needed. Clicking outside an open badge (and not inside its controlled element) automatically closes it.

**Badge IDs:** Use `{description-element-id}-badge` for badge button IDs.

Agents must not:

- render explanatory text as always-visible paragraphs under headings
- add visible `<p>` descriptions to new pages without the info-badge toggle
- duplicate the toggle binding in page-specific scripts (navigation.js handles it)

### Styles {#styles}

Style placement rules:

- shared shell/layout styles: `ui/styles/shell.css`, `ui/styles/base.css`, `ui/styles/components.css`
- section/page styles: `ui/styles/pages/`
- stylesheet aggregation: `ui/styles/styles.css`

When adding styles:

- extend an existing section stylesheet first if the new UI belongs clearly to that section
- if a page needs its own stylesheet, place it under `ui/styles/pages/` with a clear section-oriented name
- wire new page styles through `ui/styles/styles.css`

### Assets And Media {#assets-and-media}

Current frontend asset source of truth is `ui/assets/`, not `ui/media/`.

Rules:

- Vite-consumed frontend assets go in `ui/assets/`
- repo reference media that is not part of the app bundle may go in `media/`
- do not create a parallel `ui/media/` convention unless the repo is explicitly migrated to it

---

## Vite Build And UI Routing {#vite-build-and-ui-routing}

### Build Requirements {#build-requirements}

For a new UI page to exist correctly:

1. create the HTML file under `ui/`
2. add the HTML file to the `input` object in `ui/vite.config.ts`
3. ensure the page loads the correct page entry script or React entrypoint
4. run `npm run build` in `ui/`
5. verify the generated file appears in `ui/dist/`

### Route Requirements {#route-requirements}

Served HTML routes live in `backend/routes/ui.py`.

When adding a new page, agents must:

1. add the built page route to `UI_HTML_ROUTES` in `backend/routes/ui.py`
2. add redirect routes there if the section needs a root redirect or a legacy alias
3. avoid putting page route registration into `backend/main.py`

Agents must not assume a built HTML file is automatically served just because it exists in `ui/dist/`.

---

## Tool Input/Output Contract {#tool-input-output-contract}

Every tool in the catalog that can be used as a workflow step must declare its input and output fields. These fields drive:
- DB sync (stored in `inputs_schema_json` and `outputs_schema_json` on the `tools` table)
- Frontend tool manifest (`ui/scripts/tools-manifest.js`) for dynamic form rendering in the automation canvas
- Backend validation in `validate_automation_definition()`
- Execution engine dispatch and `inputs_json` tracking in `automation_run_steps`

### Field Descriptor Format {#field-descriptor-format}

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

### Supported Types {#supported-types}

- `string` — single-line text input
- `text` — multiline textarea
- `number` — numeric input
- `select` — dropdown; requires `options` list

### Adding a New Tool with I/O Contract {#adding-a-new-tool-with-io-contract}

1. Add the tool to `DEFAULT_TOOL_CATALOG` in `backend/tool_registry.py` with `inputs` and `outputs` lists
2. Add the execution handler in `backend/services/support.py`:
   - Read inputs via `_get_tool_input(step, "key", context)`
   - Return `RuntimeExecutionResult` with `output` as a dict keyed by output field keys
   - Add dispatch in `execute_automation_step()` tool handler
3. Add required-input validation in `validate_automation_definition()`
4. Run `node scripts/generate-tools-manifest.mjs` and `npm run build` in `ui/`

### Tool Step in a Workflow (User Perspective) {#tool-step-in-a-workflow-user-perspective}

- Step type `"tool"` with `tool_id` set to the tool's catalog id
- Inputs stored in `config.tool_inputs: { key: value }` (template variables supported)
- Outputs available as `{{steps.<step_name>.<output_key>}}` in downstream steps
- Example: a coqui-tts step named `tts` exposes `{{steps.tts.audio_file_path}}`

### Policy {#tool-io-policy}

Only add tools to the catalog when:
- A backend execution handler is designed and implemented
- Input/output schemas are defined
- The tool page (`ui/tools/<id>.html`) and script (`ui/scripts/tools/<id>.js`) exist

Do not add placeholder tools. Remove tools from the catalog if their execution backend is removed.

### Currently Implemented Tools {#currently-implemented-tools}

| Tool ID | Inputs | Key Outputs |
|---------|--------|-------------|
| `coqui-tts` | text (req), output_filename, speaker, language | `audio_file_path` |
| `llm-deepl` | user_prompt (req), system_prompt, model_identifier | `response_text`, `model_used` |
| `smtp` | relay_host (req), relay_port (req), from_address (req), to (req), subject (req), body (req), relay_security, relay_username, relay_password | `status`, `message` |

---

## Tool Registration Requirements {#tool-registration-requirements}

Tools are registered by backend catalog plus database sync, not by static frontend markup and not by per-tool JSON files.

### Source Of Truth {#tool-registration-source-of-truth}

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

### Required Metadata Fields {#required-metadata-fields}

- `id`
- `name`
- `description`

Validation rules:

- every registered tool must have a backend catalog entry
- all required fields must be non-empty strings
- `id` values must remain stable because they map to DB rows, routes, pages, and sidenav items

### Tool Folder Rules {#tool-folder-rules}

The top-level `tools/` folder is not currently used for registration.

If future tool-specific collateral is needed:

- use `tools/<tool-id>/` for documentation, helper scripts, sample configs, or non-app collateral
- do not create `tools/<tool-id>/tool.json` as a registration source
- do not move frontend page logic there
- do not move primary backend route/service logic there

Primary app code still belongs in `backend/` and `ui/`.

### Tool Change Workflow {#tool-change-workflow}

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

### Example Tool Metadata {#example-tool-metadata}

```python
{
  "id": "rss-poller",
  "name": "RSS Poller",
  "description": "Fetch RSS feeds on a schedule and emit normalized entries for downstream automations.",
}
```

### Example Verification Flow {#example-verification-flow}

1. Add `rss-poller` to the default tool catalog in `backend/tool_registry.py`.
2. Run `node scripts/generate-tools-manifest.mjs`.
3. Run `npm run build` in `ui/`.
4. Open `/tools/catalog.html`.
5. Confirm the tool card and sidenav entry appear with the expected label and description.

---

## Generated And Runtime Files {#generated-and-runtime-files}

Agents must not hand-edit generated or runtime artifact files unless the task explicitly targets them:

- `ui/dist/**`
- `ui/scripts/tools-manifest.js` without also regenerating it from the script
- runtime database objects directly as a substitute for schema/code changes
- `ui/node_modules/**`
- `node_modules/**`

If a generated file is expected to change, regenerate it from its source workflow and mention that in verification.

---

## Testing And Verification {#testing-and-verification}

Every meaningful code change should include the smallest relevant verification set.

### Backend {#testing-backend}

- run targeted `pytest` files in `tests/`
- add or update API tests for route, schema, or DB behavior changes

### Frontend {#testing-frontend}

- run `npm run build` in `ui/` for page wiring, Vite input, or asset changes
- run `npm run test` in `ui/` for React test coverage when React code changes
- manually verify the served page route if HTML/script wiring changed

### Verification Minimum {#verification-minimum}

For code changes, agent responses must tell the user:

- what to run
- what should happen
- what to click or inspect to confirm the result

---

## Practical Do And Do Not Rules {#practical-do-and-do-not-rules}

Do:

- follow the existing DB-backed tool flow
- keep page entrypoints matched to page paths
- keep shared shell config centralized
- place tests beside the backend feature area they cover or under the React feature they cover
- prefer additive schema evolution over one-off DB edits

Do not:

- create a second source of truth for tools, routes, or settings
- put new page-entry logic into random root-level script files
- hardcode navigation that belongs to the shell
- edit `ui/dist/` directly
- assume `backend/main.py` is the place for new HTML routes
