# AGENTS.md

## Purpose

Agents are automated workers that execute tasks within the middleware system.

They may run automations, call APIs, process responses, or coordinate with external tools.
Agents operate independently from the UI and interact with the system primarily through the API layer.

The middleware acts as the central coordinator, while agents perform the actual execution work.

---

## Machine-Readable Policy

### Required Workflow

1. Execute work in small, testable steps.
2. Validate each step before moving to the next.
3. Log intermediate outcomes when a task has multiple stages.
4. Include testing instructions whenever code or behavior changes.

### GitHub Update Workflow

When the user says to "update github", agents must use this git workflow:

1. run `git add .`
2. run `git commit -m "<logical, task-specific message>"`
3. run `git push`

Rules:

- do not use an empty or generic commit message
- choose a concise commit message that reflects the actual change
- do not run `git push` before `git commit`, because the new changes would not be included

### Required Output For Development Work

Every development-oriented response must include:

- testing instructions
- expected behavior
- verification steps

### UI Requirements

For any UI-facing implementation or update:

- every rendered structural or interactive element must have a stable, deterministic `id`
- CSS classes must be semantic and purpose-based
- utility-first or presentation-only class naming should be avoided

### Shared Shell Requirements

Navigation and brand markup are registered by shared shell convention, not by page-local copy/paste.

Required frontend shell sources:

- `ui/scripts/shell-config.js`
- `ui/scripts/navigation.js`

When adding or changing UI pages that use the main application shell, agents must:

1. update shared navigation or brand definitions in `ui/scripts/shell-config.js` when the shell changes
2. use `data-section`, `data-sidenav-item`, and `data-shell-path-prefix` on shell pages
3. render shell placeholders with `id="topnav"` and `id="sidenav"` instead of hardcoded nav markup
4. keep the Malcom brand in the side navigation header, not as a one-off page variation
5. ensure React shell implementations consume the same shared config instead of duplicating nav labels or hrefs

Agents must not hardcode new top navigation or side navigation structures directly into individual HTML pages when the shared shell applies.

### Vite Build Requirements

For new UI pages to be included in the build and served correctly:

- Add new HTML files to the `input` object in `ui/vite.config.ts` using the format: `pageName: resolve(__dirname, "path/to/page.html")`
- Create redirect pages (e.g., `section.html`) that redirect to the main page (e.g., `section/overview.html`) for top-level navigation consistency
- Ensure `npm run build` includes the new pages in `dist/` and `npm run dev` serves them without errors
- Validate that new pages load properly in both development and production builds

### Media Requirements

For new UI media:

- store files in `ui/media/`
- do not add new media under alternative folders such as `ui/assets/`
- prefer references that make the media location obvious and consistent

### Tool Registration Requirements

Tools are registered by the backend tool catalog and database-backed manifest flow, not by hardcoded UI markup.

Source of truth:

- `backend/tool_registry.py` for the default tool catalog seed data
- the `tools` table in SQLite for persisted tool records, enabled state, and metadata overrides
- `ui/scripts/tools-manifest.js` as the generated frontend manifest
- `scripts/generate-tools-manifest.mjs` to regenerate the manifest after catalog changes

Required metadata fields:

- `id`
- `name`
- `description`

Validation rules:

- every registered tool must have a backend catalog entry
- all required fields must be non-empty strings
- `id` values must remain stable because they map to routes, DB records, and sidenav items

When adding or changing tools, agents must:

1. create or update the tool catalog entry in `backend/tool_registry.py`
2. run `node scripts/generate-tools-manifest.mjs`
3. verify that `ui/scripts/tools-manifest.js` is updated
4. add or update `ui/tools/<tool-id>.html` for the tool configuration page
5. add the page to `ui/vite.config.ts`
6. add the served HTML route in `backend/main.py`
7. verify that `ui/tools/catalog.html` renders the tool without manual card markup changes
8. verify that the tools sidenav includes the tool without hardcoded shell edits outside the generated manifest flow

Agents must not hardcode new tools directly in `ui/tools/catalog.html` or `ui/scripts/tools.js`.
Agents must not manually hardcode tool sidenav links in individual tool pages when the shared shell applies.
Agents must not add new `tools/<tool-id>/tool.json` files for tool registration.

---

## Example Tool Metadata

```python
{
  "id": "rss-poller",
  "name": "RSS Poller",
  "description": "Fetch RSS feeds on a schedule and emit normalized entries for downstream automations.",
}
```

## Example Verification Flow

1. Add `rss-poller` to the default tool catalog in `backend/tool_registry.py`.
2. Run `node scripts/generate-tools-manifest.mjs`.
3. Open `ui/tools/catalog.html`.
4. Confirm the rendered card appears with the expected label and description.
