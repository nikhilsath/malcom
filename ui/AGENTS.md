# ui/AGENTS.md

Root policy remains authoritative in AGENTS.md.
This file defines UI-domain implementation rules and should be read after root routing.

## Scope

Applies to frontend page wiring, shared shell usage, UI behavior constraints, style placement, and UI build/route integration.

---

## Repo Map (Frontend)

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

---

## File Placement Rules (Frontend)

### Frontend Entry Rules

Frontend entry modes are React and vanilla.

#### React Pages

React pages mount from `ui/src/`.

Rule:

- if a page is React-driven, its HTML must load a `ui/src/<feature>/main.tsx` or `main.ts` entry
- React components and tests stay under that same `ui/src/<feature>/` tree

#### Vanilla Pages

Vanilla pages must use page-specific entry files under `ui/scripts/<section>/`.

Rule:

- `ui/<section>/<page>.html` must load `ui/scripts/<section>/<page>.js`
- page-specific DOM bindings, listeners, and page orchestration belong in that page module or modules under the same folder
- shared code for a section belongs under the same section folder, not in a new random root-level script

Legacy root-level scripts may be imported by page-specific entry files, but new page entry files must not be added at the root of `ui/scripts/`.

---

## Shared Shell Requirements

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

---

## Connector Boundary Requirements

Connector entity lifecycle and auth-policy writes are connector-domain operations, not app settings writes.

Rules:

1. Do not route connector create/update/delete/auth-policy actions through `PATCH /api/v1/settings`.
2. Use connector endpoints (`/api/v1/connectors`, `/api/v1/connectors/auth-policy`) for connector entity writes.
3. For automation builder catalogs, consume only canonical endpoints:
  - `GET /api/v1/automations/workflow-connectors`
  - `GET /api/v1/connectors/activity-catalog`
  - `GET /api/v1/connectors/http-presets`
4. Do not add UI-owned provider availability lists or duplicate catalog definitions when backend resolver responses already exist.

---

## Selection-Driven Detail View Policy

When a page presents a directory, list, or table of selectable records, keep record details hidden in the default state and reveal them on demand in a shared modal after explicit selection, unless a documented operational reason requires an inline detail pane.

Rules:

1. Do not auto-open, auto-select, or auto-populate a detail view during initial page load.
2. Do not reserve persistent layout space for an empty detail pane before the user selects a record.
3. Use the shared modal pattern for inspect, edit, and detail flows launched from row, card, or list selection.
4. Preserve keyboard access for selection triggers and manage focus correctly when opening and closing the modal.
5. Inline detail panes are exceptions and must be justified by a continuous monitoring, side-by-side comparison, or similarly documented workflow need.
6. When an inline exception is approved, keep the justification near the implementation notes or policy-relevant page guidance so future changes do not normalize the exception.

Agents must not:

- show record details by default before the user selects a record
- leave a permanently empty detail column or panel visible in the default state
- replace the shared modal flow with a custom non-modal detail reveal pattern unless the inline exception is documented

---

## UI Requirements

For UI-facing work:

- every rendered structural or interactive element must have a stable, deterministic `id`
- CSS classes must be semantic and purpose-based
- utility-first or presentation-only class naming should be avoided
- default page state must be concise and scannable; keep non-essential instructional copy hidden by default

---

## Collapsible Element Pattern

Use a compact top-strip collapse control instead of a prominent action button.

Rules:

1. Collapsible sections must expose a full-width, low-visual-weight top strip with a centered or right-aligned `+` or `-` indicator.
2. The top strip control must remain visible in both expanded and collapsed states.
3. Keep the control as a real `<button type="button">` for keyboard and assistive-tech compatibility.
4. Preserve accessibility state via `aria-expanded` and `aria-controls` on the control, and `hidden` on the controlled region.
5. Keep deterministic IDs for the control, indicator element, and controlled panel.
6. Hidden collapsed content must be removed from layout (`display: none`) so collapsing actually saves viewport space.
7. Do not use primary/secondary CTA button styling for expand/collapse controls.

---

## UI Text Density Policy

Use minimal visible copy first, then progressive disclosure.

Rules:

1. Keep page-level visible text to titles, labels, and essential task guidance only.
2. Move explanatory, educational, or “how this works” content behind info badges.
3. Prefer one short sentence in visible state when context is necessary; place extended detail in badge-controlled content.
4. Avoid stacked explanatory paragraphs in default state, especially above fold.
5. Preserve accessibility state (`aria-expanded`, `aria-controls`, `hidden`) for any disclosed text.

For copy-heavy pages, reduce default visible text and preserve non-essential guidance behind existing badge disclosure behavior.

---

## Info Badge Pattern For Explanatory Text

Explanatory descriptions are hidden by default behind info badges. Titles remain visible; explanations are revealed on demand.

**Rule:** Do not render explanatory text as visible paragraphs in the default page state. Instead, place descriptions behind an `.info-badge` toggle button that exposes an `.info-badge-content` panel when clicked.

**CSS classes:**

- `.info-badge` — circular `i` button (20 × 20 px, purple tones); defined in `ui/styles/components.css`
- `.title-row` — flex row for title + badge alignment; defined in `ui/styles/base.css`

**JavaScript:** Toggle behavior is handled globally by `initInfoBadges()` in `ui/scripts/navigation.js`, which runs on every shell page. No per-page wiring is needed. Clicking outside an open badge (and not inside its controlled element) automatically closes it.

**Badge IDs:** Use `{description-element-id}-badge` for badge button IDs.

Agents must not:

- render explanatory text as always-visible paragraphs under headings
- add visible `<p>` descriptions to new pages without the info-badge toggle
- duplicate the toggle binding in page-specific scripts (navigation.js handles it)
- keep multiple long helper paragraphs visible in the default page state when badge disclosure can be used

---

## Styles

Style placement rules:

- shared shell/layout styles: `ui/styles/shell.css`, `ui/styles/base.css`, `ui/styles/components.css`
- section/page styles: `ui/styles/pages/`
- stylesheet aggregation: `ui/styles/styles.css`

## Brand Color Design System

All UI work must use the shared brand token system in `ui/styles/base.css`.

Canonical palette tokens:

- Primary deep purple: `--brand-deep` = `#341475`
- Primary purple: `--brand-primary` = `#441D81`
- Mid purple: `--brand-main` = `#5631BA`
- Bright purple: `--brand-bright` = `#783AD0`
- Highlight purple: `--brand-highlight` = `#AF50E6`
- Sky blue accent: `--accent-sky` = `#4FA8F4`
- Electric blue accent: `--accent-electric` = `#304DF5`
- Light surface neutral: `--neutral-surface` = `#E0DAED`
- Muted neutral: `--neutral-muted` = `#B4ADCD`
- Secondary text grey: `--neutral-secondary-text` = `#7A759A`

Required semantic usage:

1. Main brand/buttons/selected states must use `--brand-main` (or semantic aliases mapped to it).
2. Hover/strong emphasis must use `--brand-primary`.
3. Hero highlights/gradients must use `--brand-bright` and `--brand-highlight`.
4. Technical accent/active connector/focus states must use `--accent-sky`.
5. Stronger active blue emphasis must use `--accent-electric`.

Enforcement rules:

1. Do not introduce new hardcoded hex colors in UI CSS, HTML, JS, or TS for these roles.
2. Prefer existing semantic tokens like `--primary`, `--primary-focus`, and `--topnav-bg` that map to this palette.
3. If a new semantic color role is needed, define it in `ui/styles/base.css` as a token alias that maps to the canonical palette.
4. Keep color source of truth centralized in `ui/styles/base.css`; do not create parallel per-page palette definitions.

When adding styles:

- extend an existing section stylesheet first if the new UI belongs clearly to that section
- if a page needs its own stylesheet, place it under `ui/styles/pages/` with a clear section-oriented name
- wire new page styles through `ui/styles/styles.css`

---

## Assets And Media

Current frontend asset source of truth is `ui/assets/`, not `ui/media/`.

Rules:

- Vite-consumed frontend assets go in `ui/assets/`
- repo reference media that is not part of the app bundle may go in `media/`
- do not create a parallel `ui/media/` convention unless the repo is explicitly migrated to it

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

Agents must not assume a built HTML file is automatically served just because it exists in `ui/dist/`.
