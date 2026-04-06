Execution steps

1. [ ] [backend]
Files: backend/database.py
Action: Add SQL table definitions to `CREATE_SCHEMA_SQL` for a docs metadata store. Add tables: `docs_articles` (id, slug, title, summary, source_path, is_ai_created INTEGER DEFAULT 0, created_at, updated_at), `docs_tags` (id, tag, kind, created_at), and `docs_article_tags` (article_id REFERENCES docs_articles(id), tag_id REFERENCES docs_tags(id), PRIMARY KEY(article_id, tag_id)). Keep tables minimal and follow existing naming and timestamp conventions.
Completion check: `backend/database.py` contains the string `CREATE TABLE IF NOT EXISTS docs_articles` and `docs_tags`.

2. [ ] [backend]
Files: backend/services/docs.py
Action: Add a new service module implementing lightweight helpers:
- `sync_docs_from_repo(root_dir: Path)`: scans `docs/` (repo root) for `*.md` files and upserts metadata rows into `docs_articles` (slug from filename, source_path relative to repo, title from frontmatter or first H1), but does NOT perform full-text indexing. This runs on startup or on-demand.
- `get_article_by_slug(slug) -> dict`: reads `docs_articles` row and returns metadata + raw markdown content read from `docs/<slug>.md`.
- `search_articles(query, tags=None, boost_tags=None, limit=50) -> list[dict]`: performs a simple SQL-based search over `title`, `summary`, and `tags` with weighted scoring using `boost_tags` list (apply simple SQL CASE weight multiplier) — keep implementation simple and documented.
Completion check: `backend/services/docs.py` exists and exports the three functions `sync_docs_from_repo`, `get_article_by_slug`, and `search_articles`.

3. [ ] [backend]
Files: backend/routes/docs.py, backend/routes/api.py
Action: Add a FastAPI router `backend/routes/docs.py` with routes used by the frontend only (not intended as public API beyond the app):
- `GET /api/v1/docs` — list/search articles (query, tags, limit)
- `GET /api/v1/docs/{slug}` — get article metadata + content
- `PUT /api/v1/docs/{slug}` — update metadata and toggle `is_ai_created` flag (requires auth) — used when a user edits an AI-created article.
Include and wire the router in `backend/routes/api.py` by importing and `include_router`ing the new router.
Completion check: `backend/routes/docs.py` exists and `backend/routes/api.py` contains an import of `backend.routes.docs` and includes the router.

4. [ ] [ui]
Files: ui/page-registry.json, ui/docs/index.html, ui/src/docs/docs-app.tsx (or docs-app.js depending repo conventions), ui/scripts/shell-config.js, ui/topnav.html, ui/styles/styles.css
Action: Add a minimal docs SPA entry and UI shell changes:
- Add a served page registry entry mapping routePath `/docs/index.html` to `docs/index.html` with legacy aliases `/docs` and `/docs/`.
- Add `ui/docs/index.html` with an app mount point and minimal bundle references (follow existing page patterns).
- Add a small frontend app under `ui/src/docs/` that provides: searchable list, tag filters (freeform and controlled), article view (loads markdown via backend routes), and an edit workflow that updates article content and metadata via `PUT /api/v1/docs/{slug}`. The app should mark AI-created articles and toggle `is_ai_created` when edited.
- Add a right-aligned docs icon-only topnav item by adding an entry to `ui/scripts/shell-config.js` with `id: "nav-docs"`, an empty `label` (or visually hidden label) and `href: "docs/index.html"`. Add CSS to `ui/styles/styles.css` to right-align docs icon and to style the icon-only link. Add a small search icon in the topnav that opens the docs search when clicked.
Completion check: `ui/page-registry.json` contains `/docs/index.html` entry; `ui/scripts/shell-config.js` contains `nav-docs`; and `ui/docs/index.html` exists.

5. [ ] [docs]
Files: docs/ (new directory), docs/README.md, docs/example-how-to.md
Action: Create a `docs/` directory at repo root to hold article markdown files. Add `README.md` documenting metadata best practices (frontmatter fields: title, slug, tags[], controlled_tags[], referenced_files[]), slug convention, and developer process (how `sync_docs_from_repo` works). Include one sample `example-how-to.md` demonstrating metadata frontmatter and content.
Completion check: `docs/README.md` exists and `docs/example-how-to.md` exists.

6. [ ] [backend/test]
Files: tests/test_ui_html_routes.py, tests/api_smoke_registry/ (if API endpoints added)
Action: Update tests that inspect the UI page registry to account for the new `/docs/index.html` entry by ensuring the new `docs/index.html` file is present in `ui/dist` during the test bootstrap. If adding API routes, add smoke coverage entries under `tests/api_smoke_registry/ROUTE_SCENARIO_MAP` for the new `/api/v1/docs` routes.
Completion check: `tests/test_ui_html_routes.py` will find `docs/index.html` in the repo UI dir during its registry file existence check; `tests/api_smoke_registry` includes entries for `/api/v1/docs` if applicable.

7. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md
Action: Add a new Quick Task entry under "Quick Task -> Where to Edit" explaining where documentation page routes live and referencing the new `docs/` SPA entry and backend docs router. Update `AGENTS.md` root routing notes to include the docs area guidance.
Completion check: `AGENTS.md` contains a short mention of the docs route mapping and points to `backend/routes/docs.py` and `ui/page-registry.json`.

8. [ ] [github]
Files: See files changed above (stage only relevant files)
Action: Commit changes in a single focused commit when all steps are implemented. Commit message example: "Add documentation system: markdown storage + DB metadata, frontend docs SPA, and backend docs API". After commit, move this task file from `.github/tasks/open/TASK-018-add-documentation-system.md` to `.github/tasks/closed/TASK-018-add-documentation-system.md` in the same commit.
Completion check: `git log -1` shows the commit message above and the moved task file is under `.github/tasks/closed/` in the repo.


Test impact review

- tests/test_ui_html_routes.py — intent: ensure served UI pages are present. Action: keep; add `docs/index.html` to the UI build artifacts used in the test bootstrap. Validation command: `python -m pytest -q tests/test_ui_html_routes.py`
- tests/test_api_smoke_matrix.py & tests/api_smoke_registry/* — intent: internal API smoke coverage. Action: update/add entries for `/api/v1/docs` if backend routes are added. Validation command: `python -m pytest -q tests/test_api_smoke_matrix.py`
- ui/e2e/* (Playwright) — intent: e2e coverage for docs SPA. Action: add an e2e spec `ui/e2e/docs.spec.ts` covering search, open article, edit toggles `is_ai_created`. Validation command: `npm --prefix ui run test:e2e -- e2e/docs.spec.ts`


Testing steps

1. [ ] [test]
Files: none (test step)
Action: Run focused unit tests after implementation:
- `python -m pytest -q tests/test_ui_html_routes.py`
- `python -m pytest -q tests/test_api_smoke_matrix.py` (if API added)
Completion check: commands exit 0.

2. [ ] [test]
Files: ui/
Action: Build UI and run e2e for docs:
- `cd ui && npm run build && npm --prefix . run test:e2e -- e2e/docs.spec.ts`
Completion check: Playwright spec passes and artefacts written to `tests/test-results`.


Documentation review

1. [ ] [docs]
Files: docs/README.md, AGENTS.md, backend/AGENTS.md
Action: Write the docs/README.md describing frontmatter fields (title, slug, tags, controlled_tags, referenced_files), the `is_ai_created` flag semantics, and how to trigger `sync_docs_from_repo`. Update AGENTS.md entries as noted in Execution step 7.
Completion check: `docs/README.md` exists and AGENTS files mention docs routing.


GitHub update

1. [ ] [github]
Files: all files changed by the implementation (list only the edited/created files)
Action: Stage only the implementation files and the moved task file, commit with a focused message, and push. Example command to run as the executor:

```bash
git add backend/database.py backend/services/docs.py backend/routes/docs.py backend/routes/api.py ui/page-registry.json ui/docs/index.html ui/src/docs/* ui/scripts/shell-config.js ui/styles/styles.css docs/* AGENTS.md backend/AGENTS.md .github/tasks/open/TASK-018-add-documentation-system.md && git commit -m "Add documentation system: markdown storage + DB metadata, frontend docs SPA, and backend docs API" && git mv .github/tasks/open/TASK-018-add-documentation-system.md .github/tasks/closed/TASK-018-add-documentation-system.md && git add .github/tasks/closed/TASK-018-add-documentation-system.md && git commit --amend --no-edit && git push
```

Completion check: remote contains the commit and task file moved to `.github/tasks/closed/`.


Notes / Rationale

- Chosen hybrid model: markdown files in `docs/` make content agent- and Git-friendly; DB-backed metadata enables search, controlled tags, `is_ai_created` flag, and future versioning.
- The frontend will use internal API routes under `/api/v1/docs` (not intended as a public third-party API) to support search and edits.
- Keep SQL and service changes small and incremental to allow adding full-text indexing or an external search engine later.


If you approve this plan I will draft the concrete changes (diffs and files) for the executor to apply, or I can hand this task file off for implementation. If you want any changes to the storage schema or URL structure (e.g., use `/docs/<category>/<slug>`), tell me now and I'll update the task file accordingly.