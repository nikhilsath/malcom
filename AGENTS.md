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

### Media Requirements

For new UI media:

- store files in `ui/media/`
- do not add new media under alternative folders such as `ui/assets/`
- prefer references that make the media location obvious and consistent

### Tool Registration Requirements

Tools are registered by filesystem convention, not by hardcoded UI markup.

Required structure:

- `tools/<tool-id>/tool.json`

Required metadata fields:

- `id`
- `name`
- `description`

Validation rules:

- `tool.json` must exist for every tool folder
- `id` must exactly match the folder name
- all required fields must be non-empty strings

When adding or changing tools, agents must:

1. create or update `tools/<tool-id>/tool.json`
2. run `node scripts/generate-tools-manifest.mjs`
3. verify that `ui/scripts/tools-manifest.js` is updated
4. verify that `ui/tools.html` renders the tool without manual card markup changes

Agents must not hardcode new tools directly in `ui/tools.html` or `ui/scripts/tools.js`.

---

## Example Tool Metadata

```json
{
  "id": "rss-poller",
  "name": "RSS Poller",
  "description": "Fetch RSS feeds on a schedule and emit normalized entries for downstream automations."
}
```

## Example Verification Flow

1. Add `tools/rss-poller/tool.json`.
2. Run `node scripts/generate-tools-manifest.mjs`.
3. Open `ui/tools.html`.
4. Confirm the rendered card appears with the expected label and description.
