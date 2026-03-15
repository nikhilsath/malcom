# Copilot Instructions

## Purpose

Agents work best in this repo when they follow the real architecture instead of inventing parallel structure.

Malcom is a FastAPI application with:

- a SQLite runtime database
- server-rendered HTML entry pages built by Vite
- a mix of React pages and vanilla JavaScript pages
- database-backed tool metadata, settings, scripts, and automation state

---

## Machine-Readable Policy

### Required Workflow

1. Execute work in small, testable steps.
2. Validate each step before moving to the next.
3. Log intermediate outcomes when a task has multiple stages.
4. Include testing instructions whenever code or behavior changes.
5. Match existing repo structure before introducing a new pattern.
6. Prefer extending the current source of truth over creating a second one.

### Required Output For Development Work

Every development-oriented response must include:

- testing instructions
- expected behavior
- verification steps

---

## Repo Map

### Backend

- `backend/main.py` — FastAPI app factory, router registration, static mounts
- `backend/routes/api.py` — JSON API endpoints
- `backend/routes/ui.py` — HTML page routes and redirect routes; source of truth for served UI URLs
- `backend/database.py` — SQLite connection helpers, schema initialization, additive schema evolution via `_ensure_column`
- `backend/tool_registry.py` — default tool catalog, tool manifest generation, tool database sync logic
- `backend/services/` — backend business logic and service helpers
- `backend/schemas.py` — Pydantic request/response models
- `backend/data/malcom.db` — runtime SQLite database
- `backend/data/logs/` — application log output

### Frontend

- `ui/<section>/<page>.html` — HTML entry pages
- `ui/src/` — React/TypeScript application entrypoints and components
- `ui/scripts/` — vanilla JavaScript controllers and shared shell/runtime helpers
- `ui/styles/` — shared and page-level CSS
- `ui/assets/` — source assets consumed by Vite imports
- `ui/dist/` — generated build output; do not hand-edit

### Other

- `scripts/` — developer and maintenance scripts
- `tests/` — backend/API tests
- `tools/` — reserved for tool-owned collateral; not a registration source of truth
- `media/` — repo-level reference media only, not bundled frontend assets

---

## Database Structure

### Source Of Truth

The schema source of truth is `backend/database.py`, not the checked-in contents of `backend/data/malcom.db`.

### Schema Rules

When changing the DB schema, agents must:

1. update `backend/database.py`
2. add new `CREATE TABLE IF NOT EXISTS` definitions there if introducing a table
3. use `_ensure_column(...)` for additive column changes to existing tables
4. keep booleans as SQLite `INTEGER` values
5. keep structured payloads in `*_json` text columns unless there is a strong reason not to
6. update API serialization/deserialization logic and tests in the same task

Agents must not:

- treat `backend/data/malcom.db` as the schema source of truth
- hand-edit SQLite files directly as a substitute for code changes
- create ad hoc migration files unless the repo adopts a formal migration system first

---

## File Placement Rules

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

### Frontend Entry Rules

#### React Pages

React pages mount from `ui/src/`.

- `ui/dashboard/home.html` → `ui/src/dashboard/main.tsx`
- `ui/automations/overview.html` → `ui/src/automation/main.tsx`
- `ui/scripts/library.html` → `ui/src/scripts-library/main.ts`

Rule: if a page is React-driven, its HTML must load a `ui/src/<feature>/main.tsx` or `main.ts` entry.

#### Vanilla Pages

Vanilla pages must use page-specific entry files under `ui/scripts/<section>/`.

Rule: `ui/<section>/<page>.html` must load `ui/scripts/<section>/<page>.js`

Examples:

- `ui/apis/outgoing.html` → `ui/scripts/apis/outgoing.js`
- `ui/settings/workspace.html` → `ui/scripts/settings/workspace.js`
- `ui/tools/llm-deepl.html` → `ui/scripts/tools/llm-deepl.js`

Agents must not add new page entry files at the root of `ui/scripts/`.

### Shared Shell Requirements

Navigation and brand markup are registered by shared shell convention, not by page-local copy/paste.

Required shell sources: `ui/scripts/shell-config.js`, `ui/scripts/navigation.js`

When adding or changing UI pages that use the shell, agents must:

1. update shared navigation or brand definitions in `ui/scripts/shell-config.js` when shell navigation changes
2. use `data-section`, `data-sidenav-item`, and `data-shell-path-prefix` on shell pages
3. render shell placeholders with `id="topnav"` and `id="sidenav"`
4. keep the Malcom brand in the shared shell, not page-local markup
5. avoid duplicating nav labels or hrefs inside individual pages

### UI Requirements

- every rendered structural or interactive element must have a stable, deterministic `id`
- CSS classes must be semantic and purpose-based
- utility-first or presentation-only class naming should be avoided

### Styles

- shared shell/layout styles: `ui/styles/shell.css`, `ui/styles/base.css`, `ui/styles/components.css`
- section/page styles: `ui/styles/pages/`
- stylesheet aggregation: `ui/styles/styles.css`

---

## Vite Build And UI Routing

### Build Requirements

For a new UI page to exist correctly:

1. create the HTML file under `ui/`
2. add the HTML file to the `input` object in `ui/vite.config.ts`
3. ensure the page loads the correct page entry script or React entrypoint
4. run `npm run build` in `ui/`
5. verify the generated file appears in `ui/dist/`

### Route Requirements

Served HTML routes live in `backend/routes/ui.py`.

When adding a new page, agents must:

1. add the built page route to `UI_HTML_ROUTES` in `backend/routes/ui.py`
2. add redirect routes there if the section needs a root redirect or a legacy alias
3. avoid putting page route registration into `backend/main.py`

---

## Tool Input/Output Contract

Every tool in the catalog that can be used as a workflow step must declare its input and output fields.

### Field Descriptor Format

```python
{
    "key": "text",          # machine-readable key
    "label": "Text to Speak",  # human-readable label
    "type": "text",         # string | text | number | select
    "required": True,       # inputs only
    "options": ["a", "b"],  # select type only
}
```

### Adding a New Tool with I/O Contract

1. Add the tool to `DEFAULT_TOOL_CATALOG` in `backend/tool_registry.py` with `inputs` and `outputs` lists
2. Add the execution handler in `backend/services/support.py`
3. Add required-input validation in `validate_automation_definition()`
4. Run `node scripts/generate-tools-manifest.mjs` and `npm run build` in `ui/`

---

## Tool Registration Requirements

Tools are registered by backend catalog plus database sync — not by static frontend markup and not by per-tool JSON files.

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

Agents must not:

- hardcode new tools directly into `ui/tools/catalog.html` or `ui/scripts/tools.js`
- manually hardcode tool sidenav links on individual pages
- add `tools/<tool-id>/tool.json` files for registration

---

## Generated And Runtime Files

Agents must not hand-edit:

- `ui/dist/**`
- `ui/scripts/tools-manifest.js` without also regenerating it from the script
- `backend/data/malcom.db` as a substitute for schema/code changes
- `ui/node_modules/**` or `node_modules/**`

---

## Testing And Verification

### Backend

- run targeted `pytest` files in `tests/`
- add or update API tests for route, schema, or DB behavior changes

### Frontend

- run `npm run build` in `ui/` for page wiring, Vite input, or asset changes
- run `npm run test` in `ui/` for React test coverage when React code changes

---

## Practical Do And Do Not Rules

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
