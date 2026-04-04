# AGENTS.md

## Entry Point Routing {#entry-point-routing}

Prefer starting prompts with `[AREA: <keyword>]` to scope which policy files apply.

| Keyword | Read These Files | Skip These Files |
|---|---|---|
| `db` | `AGENTS.md` + `backend/AGENTS.md` + `tests/AGENTS.md` | `ui/AGENTS.md` |
| `ui` | `AGENTS.md` + `ui/AGENTS.md` + `tests/AGENTS.md` | `backend/AGENTS.md` except connector boundary rules in root |
| `tools` | `AGENTS.md` + `backend/AGENTS.md` + `ui/AGENTS.md` + `tests/AGENTS.md` | none |
| `api` | `AGENTS.md` + `backend/AGENTS.md` + `tests/AGENTS.md` | `ui/AGENTS.md` |
| `test` | `AGENTS.md` + `tests/AGENTS.md` + matching domain file | unrelated domain files |
| `automation` | `AGENTS.md` + `backend/AGENTS.md` + `ui/AGENTS.md` + `tests/AGENTS.md` | none |
| `nav` | `AGENTS.md` + `ui/AGENTS.md` + `tests/AGENTS.md` | `backend/AGENTS.md` except global rules in root |
| `scripts` | `AGENTS.md` + `backend/AGENTS.md` + `tests/AGENTS.md` | `ui/AGENTS.md` |
| `audit` | `AGENTS.md`, then the closest domain AGENTS file for the current review batch | unrelated domain files until the batch reaches them |

If no `[AREA:]` prefix is present, read Quick Task -> Where to Edit first.
If the task clearly maps to one area, infer the closest matching area and load only the referenced domain files.
If the task is ambiguous across multiple areas, stop before loading domain-specific policy files, list the supported area keywords, and ask the user to choose one.

### Domain Policy Files

After reading root routing and machine index, load the closest domain AGENTS file when relevant:

- `backend/AGENTS.md` for backend, schema, and tool/backend contract work
- `ui/AGENTS.md` for frontend structure, shell, styles, and route wiring work
- `tests/AGENTS.md` for verification workflow, smoke coverage, and startup/test triage

### Repository Audit Area {#repository-audit-area}

Use `[AREA: audit]` for repository-wide review tasks that cannot be completed in one pass, such as architecture audits, dead-code scans, policy conformance reviews, or broad fileset walkthroughs.

Audit rules:

1. Use `.agents/repo-scan-index.md` as the source of truth for repo-review progress.
2. Review the repo in small batches by folder, subsystem, or another explicit scope; do not treat the whole repository as one undifferentiated pass.
3. Load only the closest domain policy file for the current batch instead of loading every domain file up front.
4. Update the tracker as work progresses using these statuses: `pending`, `in_progress`, `reviewed`, `needs_followup`, `blocked`, `skip_generated`.
5. Mark a file as `reviewed` only after it has been opened and assessed for the stated audit scope.
6. Use `needs_followup` for files that were inspected but need a second pass, and `skip_generated` for generated or forbidden paths that are intentionally excluded.
7. Do not keep duplicate ad hoc progress trackers in task notes when `.agents/repo-scan-index.md` already covers the audit.
8. Do not claim a repo-wide review is complete unless every in-scope non-skipped file for that audit has been accounted for in the tracker.

For `[AREA: audit]` responses, include the current batch, what was completed, what still needs follow-up, and the next recommended batch.

---

## Purpose

Machine-only policy file.

Primary objective: deterministic routing, file targeting, and enforcement rules for agent behavior in this repository.

---

## Machine-Readable Policy

### Required Workflow {#required-workflow}

1. Execute work in small, testable steps.
2. Validate each step before moving to the next.
3. Build or update the smallest relevant automated tests in the same change as behavior changes.
4. Log intermediate outcomes when a task has multiple stages.
5. Include expected behavior whenever code or behavior changes.
6. Match existing repo structure before introducing a new pattern.
7. Prefer extending the current source of truth over creating a second one.
8. Keep files narrowly responsible; factor new concerns into adjacent modules or helpers instead of growing catch-all files.
9. Fix the canonical path instead of layering fallbacks, duplicate reads, or shadow writes when the root cause can be corrected directly.
10. When runtime-managed entities already live in the database, persisted rows plus their canonical resolvers are the runtime source of truth.

### Implementation Quality And Source Of Truth {#implementation-quality-and-source-of-truth}

1. Keep files narrowly responsible; when a task adds a new concern to an already-large file, extract or extend a neighboring module or service instead of appending another responsibility to the largest file in the area.
2. Do not resolve architectural drift by adding fallback branches, shadow settings, compatibility reads, or duplicate write paths when the canonical path can be fixed directly.
3. Temporary fallbacks are allowed only when a staged migration or external compatibility contract requires them, and the same change must document the canonical owner plus an explicit removal follow-up.
4. When entities, catalogs, presets, enablement, or provider state already live in the database, DB-backed resolvers and persisted rows are the runtime source of truth.
5. Seed constants may bootstrap DB state, but they must not become a parallel runtime registry once persisted data and resolvers exist.

### GitHub Update Workflow {#github-update-workflow}

When the user says to "update github", agents must use this git workflow:

1. stage only the files relevant to the requested change
2. run `git commit -m "<logical, task-specific message>"`
3. run `git push`

This may be run as a single terminal line:

`git add <relevant-files> && git commit -m "<logical, task-specific message>" && git push`

Rules:

- do not use an empty or generic commit message
- choose a concise commit message that reflects the actual change
- do not run `git push` before `git commit`, because the new changes would not be included

### Required Output For Development Work {#required-output-for-development-work}

Every development-oriented response must include:

- expected behavior

This requirement applies only when the user asked for implementation, debugging, code changes, behavior changes, or verification of changed behavior.
It does not apply to direct questions, policy edits, meta-instructions, or requests for brief answers unless the user also asked for development workflow detail.

### Response Scope And Instruction Fidelity {#response-scope-and-instruction-fidelity}

Response policy (normative):

1. Answer only the explicit user request.
2. Do not add unrequested rationale, guidance, or adjacent tasks.
3. Do not expand scope unless the user explicitly asks.
4. When instructions conflict, follow the latest user instruction literally.
5. Default to shortest complete response.
6. Ask permission before adding optional elaboration.
7. If user corrects behavior, address only the correction.

### Maintenance Sync Rule {#maintenance-sync-rule}

When updating policy, agents must update all of the following in the same change when applicable:

1. canonical prose rules
2. `Quick Task -> Where to Edit` reference table
3. `Rules Matrix` entries
4. machine index block between `MACHINE_INDEX_START` and `MACHINE_INDEX_END`

Whenever `AGENTS.md` is updated, `scripts/check-policy.sh` must be updated in the same change to reflect new or changed enforcement rules.

Do not leave machine reference content stale after changing source rules.

---

## Connector And Tool Boundary {#connector-and-tool-boundary}

Use one integration model per responsibility. Do not blur remote API access, HTTP request definitions, and machine-executed runtimes.

### Routing Rule {#connector-boundary-routing-rule}

When deciding where a new integration belongs, agents must:

1. use connectors plus outgoing APIs, connector workflow activities, or automation HTTP steps for remote SaaS/API integrations, OAuth credentials, provider presets, reusable auth/base URL state, and provider-aware builder actions
2. use the tool catalog only for locally executed binaries, managed runtimes, worker-bound services, or other non-HTTP machine capabilities
3. when adding a connector provider, also decide whether it needs prebuilt workflow activities and define them in the connector activity system when appropriate
4. keep generic HTTP steps available for raw/custom API usage instead of overfitting every remote action into the activity catalog
5. avoid creating a second source of truth when an integration is already representable as a connector-backed HTTP request or connector activity

### Connector Route/Service Boundary {#connector-route-service-boundary}

Connector HTTP routes must stay thin when provider-specific credential lifecycle logic exists.

Rules:

1. Keep provider-specific connector business logic, including OAuth token exchange, refresh, and revoke handlers, in dedicated `backend/services/connector_<provider>*.py` or adjacent connector service modules.
2. Keep `backend/routes/connectors.py` focused on HTTP parameter extraction, response shaping, redirects, and dependency wiring rather than provider-specific OAuth token lifecycle implementations.
3. Do not make backend services import connector route helpers as the source of truth for provider-specific connector business logic.
4. GitHub OAuth setup may resolve omitted client credentials from `MALCOM_GITHUB_OAUTH_CLIENT_ID` and `MALCOM_GITHUB_OAUTH_CLIENT_SECRET`; the OAuth app redirect URI remains `/api/v1/connectors/github/oauth/callback`. Trello OAuth may resolve omitted client credentials from `MALCOM_TRELLO_OAUTH_CLIENT_ID` and `MALCOM_TRELLO_OAUTH_CLIENT_SECRET`; the default callback path is `/api/v1/connectors/trello/oauth/callback`.

### Workflow Builder Connector Source Of Truth {#workflow-builder-connector-source-of-truth}

Workflow-builder connector dropdown/options must follow one explicit resolver path:

1. persistence source: `connectors` table rows
2. backend resolver: `backend/services/workflow_builder.py:list_workflow_builder_connectors`
3. API surface: `GET /api/v1/automations/workflow-connectors` in `backend/routes/automations.py`
4. UI consumer: automation builder support loading in `ui/src/automation/app.tsx`

Rules:

1. Do not source workflow-builder connector options directly from generic settings payloads in the UI when a dedicated resolver endpoint exists.
2. Do not add parallel hardcoded connector availability lists in UI or route handlers.
3. Canonical provider normalization for builder options must happen in the backend resolver, not ad hoc in multiple UI components.
4. Any mismatch between DB connector records, backend builder option responses, and rendered builder options is an architectural failure and must be fixed in the same task.

---

## Database Schema {#database-schema}

`backend/database.py` is the schema source of truth for structure changes and for repo-facing schema documentation.

When schema tables or table groups change, update `AGENTS.md` and `README.md` in the same change so the documented structure stays aligned with `backend/database.py`.

Current schema groups defined there:

- API registry: `inbound_apis`, `inbound_api_events`, `outgoing_scheduled_apis`, `outgoing_continuous_apis`, `webhook_apis`, `webhook_api_events`, `outgoing_delivery_history`
- Workspace state: `tools`, `tool_configs`, `settings`, `integration_presets`, `connectors`, `connector_auth_policies`, `connector_endpoint_definitions`
  Saved connector instances are canonical in `connectors`, workspace credential policy is canonical in `connector_auth_policies`, and legacy `settings.connectors` rows are migration-only input.
- Automation runtime: `automations`, `automation_steps`, `automation_runs`, `automation_run_steps`, `runtime_resource_snapshots`
- Script library: `scripts`
- Log schema: `log_db_tables`, `log_db_columns`
- Storage: `storage_locations`, `repo_checkouts`
  Persisted storage destination rows (`storage_locations`) are the runtime source of truth for local folders, Google Drive folders, and repo roots. `repo_checkouts` tracks managed GitHub repo clones linked to a storage location.

---

## Machine Reference Index {#machine-reference-index}

Machine-first routing index. Use for task-to-file targeting before consulting canonical rule text.

### Quick Task -> Where to Edit {#quick-task-where-to-edit}

| Task | Primary Files | Also Check | Must Not Edit |
|---|---|---|---|
| Add backend API route | `backend/routes/api.py` | `backend/AGENTS.md`, `tests/AGENTS.md`, `tests/test_<feature>.py` | `ui/dist/**` |
| Add served UI page route | `backend/routes/ui.py` | `ui/AGENTS.md`, `ui/vite.config.ts`, `ui/<section>/<page>.html` | `backend/main.py` (for UI routes) |
| Change DB schema | `backend/database.py` | `backend/AGENTS.md`, related serializers + tests | runtime database objects directly |
| Document database schema | `AGENTS.md`, `README.md` | `backend/database.py`, `backend/AGENTS.md`, `scripts/check-policy.sh` | runtime database objects directly |
| Add or update connector-backed remote API integration | `backend/routes/connectors.py`, `backend/routes/apis.py`, `backend/services/connector_activities.py` | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | `backend/tool_registry.py` unless local runtime/executable is required |
| Refactor connector OAuth/service boundary | `backend/services/connector_oauth.py`, `backend/services/connector_*oauth*.py`, `backend/routes/connectors.py` | `backend/AGENTS.md`, `tests/AGENTS.md`, `tests/test_connectors_api.py`, `tests/test_connector_oauth_service.py`, `scripts/check-policy.sh` | provider-specific OAuth token lifecycle helpers in `backend/routes/connectors.py` |
| Refactor workflow-builder connector option flow | `backend/services/workflow_builder.py`, `backend/routes/automations.py`, `ui/src/automation/app.tsx` | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md`, `README.md` | duplicate connector option lists in UI components |
| Update Google connector onboarding flow | `ui/settings/connectors.html`, `ui/scripts/settings/connectors.js`, `ui/scripts/settings/connectors/` | `ui/AGENTS.md`, `backend/routes/connectors.py`, `ui/e2e/`, `README.md` | browser `prompt()` dialogs for OAuth credentials |
| Add or update tool registration | `backend/tool_registry.py` | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | hardcoded tool cards/nav links |
| Refactor oversized or mixed-responsibility implementation | closest feature module + adjacent service/helper files | matching domain `AGENTS.md`, matching tests | dumping new responsibilities into the largest existing file without need |
| Fix DB-backed source-of-truth drift | canonical DB-backed resolver/service + matching tests | `backend/AGENTS.md`, `README.md` if schema/docs are affected | fallback reads/writes, hardcoded mirrors, duplicate availability lists |
| Add vanilla page logic | `ui/scripts/<section>/<page>.js` | `ui/AGENTS.md`, matching HTML + styles, `ui/e2e/` | new root-level page entry in `ui/scripts/*.js` |
| Add React page logic | `ui/src/<feature>/` | `ui/AGENTS.md`, matching HTML entry + tests, `ui/e2e/` | unrelated section folders |
| Reduce UI text density / badge migration | `ui/<section>/<page>.html` | `ui/AGENTS.md`, `ui/scripts/navigation.js`, style files | visible explanatory paragraphs in default page state |
| Add or update collapsible UI section | `ui/src/<feature>/` or `ui/<section>/<page>.html` | `ui/AGENTS.md`, `ui/styles/pages/**`, related tests | oversized CTA-style collapse buttons or non-collapsing hidden states |
| Convert list/detail UI to selection-driven modal details | `ui/src/<feature>/` or `ui/<section>/<page>.html` | `ui/AGENTS.md`, shared modal utilities, related tests | auto-open detail panes on load or permanent empty inline detail columns |
| Update shared shell navigation | `ui/scripts/shell-config.js` | `ui/AGENTS.md`, `ui/scripts/navigation.js`, shell page attributes, `ui/e2e/` | page-local duplicated topnav/sidenav markup |
| Implement or change behavior | feature source files + matching tests | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | shipping behavior changes without relevant automated tests |
| Change generated tool manifest | `scripts/generate-tools-manifest.mjs` | `backend/AGENTS.md`, regenerate `ui/scripts/tools-manifest.js` | hand-edit `ui/scripts/tools-manifest.js` without regeneration |
| Improve testing workflow | `pytest.ini`, test scripts, `scripts/check-policy.sh`, smoke registry, `ui/e2e/` | `tests/AGENTS.md`, `ui/playwright.config.ts`, `README.md` | `ui/dist/**` |
| Troubleshoot startup or Playwright execution blockers | `scripts/dev.py`, `scripts/run_playwright_server.sh`, `ui/playwright.config.ts` | `tests/AGENTS.md`, `backend/data/logs/`, `README.md` | skipping listener/process diagnostics |
| Audit repo-wide file coverage or architecture in batches | `.agents/repo-scan-index.md`, current batch files | matching domain AGENTS file, `AGENTS.md` | duplicate ad hoc progress trackers |
| Update agent response policy or instruction-following rules | `AGENTS.md`, `scripts/check-policy.sh`, domain AGENTS files | `Required Output`, `Response Scope`, `Rules Matrix`, `MACHINE_INDEX_START` | unrelated app source files |

### Rules Matrix {#rules-matrix}

| Rule ID | Requirement | Enforced In |
|---|---|---|
| R-ROUTE-001 | If no `[AREA:]` prefix is provided, infer the area only when the task is clearly scoped; otherwise stop before domain-specific work and ask the user to choose from the supported area keywords | Prompt routing and policy loading |
| R-AUDIT-001 | `[AREA: audit]` work must track repo-review progress in `.agents/repo-scan-index.md`, operate in explicit batches, and avoid duplicate progress trackers outside that file | Repo-wide review and audit workflows |
| R-ARCH-001 | Remote SaaS/API integrations use connectors plus outgoing APIs, connector workflow activities, or automation HTTP steps by default; do not model them as tools unless a local runtime/executable is required | Integration architecture and agent routing |
| R-CODE-001 | Keep files narrowly responsible; factor new concerns into adjacent modules/services instead of growing catch-all files | Implementation structure and refactors |
| R-FIX-001 | Fix the canonical path instead of layering fallback branches, shadow state, or duplicate reads/writes, except for explicit staged migrations with documented removal | Behavior fixes and architecture corrections |
| R-CONN-001 | Google connector onboarding must begin from the Connect provider control and must not collect OAuth credentials through browser prompt dialogs | Connector onboarding UX and OAuth setup flows |
| R-CONN-002 | When adding a connector provider, also evaluate and define provider-aware prebuilt workflow activities in the connector activity catalog, including scopes, input schema, output schema, and execution mapping | Connector/provider implementation workflow |
| R-CONN-003 | Provider-aware connector workflow actions must use the connector activity system, remain provider-aware in the builder with explicit selectable UI actions plus action-specific inputs/outputs, and keep generic HTTP steps available for raw/custom API calls | Automation builder connector actions |
| R-CONN-004 | Workflow-builder connector options must be served by `GET /api/v1/automations/workflow-connectors` via `backend/services/workflow_builder.py` sourced from persisted connector rows (`connectors` table); do not duplicate connector availability definitions across UI/backend layers | Workflow builder connector option architecture |
| R-CONN-005 | Provider-specific connector OAuth token lifecycle handlers belong in backend service modules, and `backend/routes/connectors.py` must not be the source of truth for those handlers or route-imported service logic | Connector route/service architecture |
| R-DB-001 | Schema source of truth is `backend/database.py` | Database changes |
| R-DB-002 | Root schema documentation in `AGENTS.md` and `README.md` must stay aligned with `backend/database.py` when tables or table groups change | Database documentation |
| R-SOT-001 | For DB-backed entities, catalogs, presets, enablement, or provider state, persisted rows plus canonical resolvers are the runtime source of truth; seed constants must not become parallel runtime registries | Backend/services, connector catalogs, and runtime configuration flows |
| R-UI-001 | Served HTML routes are registered in `backend/routes/ui.py` | UI route wiring |
| R-UI-002 | Explanatory UI descriptions use info-badge pattern | UI pages |
| R-UI-003 | Default UI state must keep helper copy minimal; non-essential guidance lives behind info badges | UI copy and page layout changes |
| R-UI-004 | Collapsible sections use a compact full-width top-strip collapse control with `+`/`-` indicator, persistent visibility, `aria-expanded` + `aria-controls` wiring, and true layout collapse (`display: none`) for hidden content | UI collapsible controls |
| R-UI-005 | Selection-driven list/detail pages keep record details hidden until explicit selection, use shared modal detail flows by default, and allow inline detail panes only for documented operational exceptions | List/detail UI behavior |
| R-TOOL-001 | Tool registration flows through backend catalog + DB sync | Tool lifecycle changes |
| R-TOOL-002 | Tool page wiring includes Vite input + UI route + page script | Tool page additions |
| R-GEN-001 | Do not hand-edit generated artifacts like `ui/dist/**` | Build outputs |
| R-GEN-002 | Regenerate `ui/scripts/tools-manifest.js` from script source | Tool catalog manifest updates |
| R-TEST-001 | Development work responses include expected behavior, but only for implementation-oriented tasks | All implementation responses |
| R-RESP-001 | Do not add unprompted explanatory text or adjacent guidance beyond the explicit user request | All responses |
| R-RESP-002 | Default to the shortest complete answer unless the user asks for more detail | All responses |
| R-RESP-003 | When user instructions conflict with default helpfulness behavior, follow the user instruction literally | All responses |
| R-POLICY-001 | Whenever `AGENTS.md` is updated, `scripts/check-policy.sh` must be updated in the same change to reflect new or changed enforcement rules | Policy maintenance and enforcement automation |
| R-TEST-002 | Use the two-tier test workflow: `scripts/test-precommit.sh` for fast local iteration and `scripts/test-full.sh` as the completion gate for user-visible workflow changes, shared frontend/test infrastructure changes, and browser coverage validation | Testing workflow changes |
| R-TEST-003 | Keep internal API smoke coverage in `tests/test_api_smoke_matrix.py` aligned with every served `/api/v1/**` route and `/health`, with cases sourced from `tests/api_smoke_registry/` | Backend route additions and removals |
| R-TEST-004 | Remove or retire a test only when the covered contract is removed or replaced, and update the replacement coverage in the same task | Test maintenance |
| R-TEST-005 | Any user-visible UI workflow change must add or update Playwright coverage in `ui/e2e/` unless the change is strictly non-behavioral | Frontend and browser workflow changes |
| R-TEST-006 | Playwright coverage must assert the changed workflow behavior, not only route load or static render | Playwright authoring and UI changes |
| R-TEST-007 | For startup, server-launch, or Playwright execution failures, verify what is already running by checking active listeners/processes on expected ports before treating the failure as unresolved | Failure recovery and test infrastructure troubleshooting |
| R-TEST-008 | Behavior-changing implementation work must add or update relevant automated tests in the same change unless the change is strictly non-behavioral | All implementation workflows |

<!-- MACHINE_INDEX_START
{
  "version": 25,
  "prompt_prefix": {
    "convention": "[AREA: <keyword>] <task description>",
    "routing_section": "#entry-point-routing",
    "keywords": ["db", "ui", "tools", "api", "test", "automation", "nav", "scripts", "audit"],
    "fallback": "Read Quick Task -> Where to Edit table in #machine-reference-index first",
    "missing_prefix_behavior": {
      "if_clearly_scoped": "Infer the closest matching area and continue with only the referenced domain files.",
      "if_ambiguous": "Stop before loading domain-specific policy files, list the supported area keywords, and ask the user to choose one."
    }
  },
  "domain_policies": {
    "backend": ["backend/AGENTS.md"],
    "frontend": ["ui/AGENTS.md"],
    "testing": ["tests/AGENTS.md"]
  },
  "primary_sources": {
    "global_routing": ["AGENTS.md"],
    "backend_rules": ["backend/AGENTS.md"],
    "ui_rules": ["ui/AGENTS.md"],
    "test_rules": ["tests/AGENTS.md"],
    "ui_html_routes": ["backend/routes/ui.py"],
    "db_schema": ["backend/database.py"],
    "database_docs": ["AGENTS.md", "README.md"],
    "repo_scan_tracker": [".agents/repo-scan-index.md"],
    "tool_catalog": ["backend/tool_registry.py"],
    "tool_manifest_generator": ["scripts/generate-tools-manifest.mjs"],
    "policy_enforcement_script": ["scripts/check-policy.sh"],
    "api_smoke_registry": ["tests/api_smoke_registry/", "tests/test_api_smoke_matrix.py"]
    ,"workflow_builder_connectors": ["backend/services/workflow_builder.py", "backend/routes/automations.py", "ui/src/automation/app.tsx"]
  },
  "task_routes": {
    "db_schema_change": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["backend/database.py"],
      "verify": ["AGENTS.md", "README.md", "tests/"]
    },
    "db_schema_documentation": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["AGENTS.md", "README.md", "scripts/check-policy.sh"],
      "verify": ["policy text and README stay aligned with backend/database.py"]
    },
    "factoring_refactor": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["closest feature module", "adjacent services/helpers"],
      "verify": ["matching automated tests", "oversized changed files were reviewed for factoring"]
    },
    "db_backed_source_of_truth_fix": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["canonical DB-backed resolver/service", "matching consumers"],
      "verify": ["persisted rows remain canonical", "duplicate code-side registries are removed or avoided", "matching automated tests"]
    },
    "ui_change": {
      "read": ["AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["ui/", "backend/routes/ui.py", "ui/vite.config.ts"],
      "verify": ["ui/e2e/", "ui/", "scripts/test-precommit.sh", "scripts/test-full.sh"]
    },
    "tool_change": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["backend/tool_registry.py", "backend/services/support.py", "ui/tools/", "ui/scripts/tools/", "ui/vite.config.ts", "backend/routes/ui.py"],
      "generate": ["scripts/generate-tools-manifest.mjs"],
      "verify": ["ui/scripts/tools-manifest.js", "ui/tools/catalog.html", "ui/e2e/"]
    },
    "test_workflow_change": {
      "read": ["AGENTS.md", "tests/AGENTS.md"],
      "edit": ["pytest.ini", "scripts/test-precommit.sh", "scripts/test-full.sh", "scripts/check-policy.sh", "tests/api_smoke_registry/", "tests/test_api_smoke_matrix.py", "ui/e2e/", "ui/e2e/README.md"],
      "verify": ["pytest", "npm run test", "npm run build", "npm run test:e2e"]
    },
    "repo_audit": {
      "read": ["AGENTS.md"],
      "edit": [".agents/repo-scan-index.md"],
      "verify": ["current batch files are accounted for with audit statuses and notes"]
    },
    "response_policy_update": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["AGENTS.md", "scripts/check-policy.sh", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "check": ["#required-output-for-development-work", "#response-scope-and-instruction-fidelity", "#maintenance-sync-rule", "#rules-matrix", "MACHINE_INDEX_START"],
      "verify": ["policy text, machine index, and scripts/check-policy.sh stay synchronized"]
    },
    "workflow_builder_connector_refactor": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["backend/services/workflow_builder.py", "backend/routes/automations.py", "ui/src/automation/app.tsx", "README.md"],
      "verify": ["tests/test_automations_api.py", "ui/src/automation/__tests__/", "ui/e2e/"]
    },
    "connector_oauth_service_boundary": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["backend/services/connector_oauth.py", "backend/services/connector_*oauth*.py", "backend/routes/connectors.py", "scripts/check-policy.sh"],
      "verify": ["tests/test_connector_oauth_service.py", "tests/test_connectors_api.py", "backend/routes/connectors.py contains no provider-specific OAuth token lifecycle helpers"]
    }
  },
  "forbidden_paths": [
    "ui/dist/**",
    "ui/node_modules/**",
    "node_modules/**"
  ],
  "response_requirements": {
    "implementation_tasks_only": [
      "expected_behavior"
    ],
    "test_creation_policy": "For behavior-changing implementation tasks, add or update relevant automated tests in the same change unless strictly non-behavioral.",
    "general_rule": "For non-implementation requests, respond with only the directly requested content unless the user asks for more detail."
  },
  "implementation_standards": {
    "factoring": "Keep files narrowly responsible; factor new concerns into adjacent modules/services instead of growing catch-all files.",
    "fix_over_fallback": "Fix the canonical path instead of layering fallbacks, duplicate reads, or shadow writes unless a staged migration explicitly requires temporary compatibility logic.",
    "db_backed_source_of_truth": "For DB-backed entities, catalogs, presets, enablement, or provider state, persisted rows plus canonical resolvers are the runtime source of truth; seed constants may bootstrap but must not become a second runtime registry."
  }
}
MACHINE_INDEX_END -->

---

## Practical Do And Do Not Rules {#practical-do-and-do-not-rules}

## Repository Indexing {#repository-indexing}

Purpose: make the repo easier for automated agents and humans to navigate by providing reproducible, machine-readable indexes and small generator scripts.

Recommended indexes (pick the subset that fits your operations):

- **File manifest:** a JSON list of workspace files with path, size, language, and basic tags. Rebuildable via `scripts/update_indices.sh` and stored under `.indices/repo_index.json`.
- **Symbol/tags index:** generated `ctags` file (`.indices/repo.tags`) for fast symbol-to-file lookups by editors and agents.
- **API route map:** JSON mapping of HTTP endpoints → handler files (use simple greps/parsers for `backend/routes/` and framework decorators). Store as `.indices/api_routes.json`.
- **Tests → code map:** mapping of tests to the modules they exercise (use `pytest --collect-only` and small post-processing), stored as `.indices/tests_index.json`.
- **Data-model registry:** short manifest linking DB tables to the services that read/write them (hand-maintained `data-models.json`), useful for data-flow questions.
- **Semantic vector index (optional):** vector embeddings of file chunks for natural-language search (store vectors metadata in `.indices/semantic/` and keep vector store off-repo if large).

Best practices:

- Keep index generators in `scripts/` (e.g., `scripts/update_indices.sh`) so they are reproducible and runnable in CI or locally.
- Store only small, derived index files in the repo under `.indices/` and ignore large vector stores; regenerate or publish artifacts in CI if needed.
- Update indices as part of changelists that modify large areas (routes, DB schema, or major refactors) and add index regeneration to relevant precommit or CI jobs where appropriate.
- Document the regeneration steps in `README.md` and reference `.indices/` in `AGENTS.md` so automated agents know where to look.

Minimal scripts to include (examples):

- `scripts/generate_repo_index.py` — produce `.indices/repo_index.json`.
- `scripts/update_indices.sh` — wrapper that runs ctags, the repo manifest generator, and API/test mappers.

Location: keep indexes under `.indices/` at the repo root and reference them from `AGENTS.md` and `.agents/repo-scan-index.md` when relevant.

When to update: regenerate indexes after structural changes (routes, schema, major refactors) and during periodic CI runs to keep them fresh.


Do:

- follow the existing DB-backed tool flow
- keep page entrypoints matched to page paths
- keep shared shell config centralized
- keep schema documentation in `AGENTS.md` and `README.md` aligned with `backend/database.py`
- keep `scripts/check-policy.sh` in sync with `AGENTS.md` policy requirements
- place tests beside the backend feature area they cover or under the React feature they cover
- add or update relevant automated tests in the same change when behavior changes
- prefer additive schema evolution over one-off DB edits
- factor new responsibilities into adjacent modules/services before extending already-large files
- fix canonical data flow directly when possible
- keep DB-backed entities, catalogs, and availability lists resolved from persisted rows

Do not:

- create a second source of truth for tools, routes, or settings
- grow large files with unrelated new responsibilities when a scoped module fits better
- solve bugs by adding shadow fallback paths when the canonical path can be repaired
- keep runtime availability or configuration duplicated in code after it exists in the database
- put new page-entry logic into random root-level script files
- hardcode navigation that belongs to the shell
- edit `ui/dist/` directly
- assume `backend/main.py` is the place for new HTML routes
