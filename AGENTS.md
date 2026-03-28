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

If no `[AREA:]` prefix is present, read Quick Task -> Where to Edit first.
If the task clearly maps to one area, infer the closest matching area and load only the referenced domain files.
If the task is ambiguous across multiple areas, stop before loading domain-specific policy files, list the supported area keywords, and ask the user to choose one.

### Domain Policy Files

After reading root routing and machine index, load the closest domain AGENTS file when relevant:

- `backend/AGENTS.md` for backend, schema, and tool/backend contract work
- `ui/AGENTS.md` for frontend structure, shell, styles, and route wiring work
- `tests/AGENTS.md` for verification workflow, smoke coverage, and startup/test triage

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

---

## Machine Reference Index {#machine-reference-index}

Machine-first routing index. Use for task-to-file targeting before consulting canonical rule text.

### Quick Task -> Where to Edit {#quick-task-where-to-edit}

| Task | Primary Files | Also Check | Must Not Edit |
|---|---|---|---|
| Add backend API route | `backend/routes/api.py` | `backend/AGENTS.md`, `tests/AGENTS.md`, `tests/test_<feature>.py` | `ui/dist/**` |
| Add served UI page route | `backend/routes/ui.py` | `ui/AGENTS.md`, `ui/vite.config.ts`, `ui/<section>/<page>.html` | `backend/main.py` (for UI routes) |
| Change DB schema | `backend/database.py` | `backend/AGENTS.md`, related serializers + tests | runtime database objects directly |
| Add or update connector-backed remote API integration | `backend/routes/connectors.py`, `backend/routes/apis.py`, `backend/services/connector_activities.py` | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | `backend/tool_registry.py` unless local runtime/executable is required |
| Update Google connector onboarding flow | `ui/settings/connectors.html`, `ui/scripts/settings/connectors.js`, `ui/scripts/settings/connectors/` | `ui/AGENTS.md`, `backend/routes/connectors.py`, `ui/e2e/`, `README.md` | browser `prompt()` dialogs for OAuth credentials |
| Add or update tool registration | `backend/tool_registry.py` | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | hardcoded tool cards/nav links |
| Add vanilla page logic | `ui/scripts/<section>/<page>.js` | `ui/AGENTS.md`, matching HTML + styles, `ui/e2e/` | new root-level page entry in `ui/scripts/*.js` |
| Add React page logic | `ui/src/<feature>/` | `ui/AGENTS.md`, matching HTML entry + tests, `ui/e2e/` | unrelated section folders |
| Reduce UI text density / badge migration | `ui/<section>/<page>.html` | `ui/AGENTS.md`, `ui/scripts/navigation.js`, style files | visible explanatory paragraphs in default page state |
| Add or update collapsible UI section | `ui/src/<feature>/` or `ui/<section>/<page>.html` | `ui/AGENTS.md`, `ui/styles/pages/**`, related tests | oversized CTA-style collapse buttons or non-collapsing hidden states |
| Convert list/detail UI to selection-driven modal details | `ui/src/<feature>/` or `ui/<section>/<page>.html` | `ui/AGENTS.md`, shared modal utilities, related tests | auto-open detail panes on load or permanent empty inline detail columns |
| Update shared shell navigation | `ui/scripts/shell-config.js` | `ui/AGENTS.md`, `ui/scripts/navigation.js`, shell page attributes, `ui/e2e/` | page-local duplicated topnav/sidenav markup |
| Implement or change behavior | feature source files + matching tests | `backend/AGENTS.md`, `ui/AGENTS.md`, `tests/AGENTS.md` | shipping behavior changes without relevant automated tests |
| Change generated tool manifest | `scripts/generate-tools-manifest.mjs` | `backend/AGENTS.md`, regenerate `ui/scripts/tools-manifest.js` | hand-edit `ui/scripts/tools-manifest.js` without regeneration |
| Improve testing workflow | `pytest.ini`, test scripts, smoke registry, `ui/e2e/` | `tests/AGENTS.md`, `ui/playwright.config.ts`, `README.md` | `ui/dist/**` |
| Troubleshoot startup or Playwright execution blockers | `scripts/dev.py`, `scripts/run_playwright_server.sh`, `ui/playwright.config.ts` | `tests/AGENTS.md`, `backend/data/logs/`, `README.md` | skipping listener/process diagnostics |
| Update agent response policy or instruction-following rules | `AGENTS.md`, domain AGENTS files | `Required Output`, `Response Scope`, `Rules Matrix`, `MACHINE_INDEX_START` | unrelated app source files |

### Rules Matrix {#rules-matrix}

| Rule ID | Requirement | Enforced In |
|---|---|---|
| R-ROUTE-001 | If no `[AREA:]` prefix is provided, infer the area only when the task is clearly scoped; otherwise stop before domain-specific work and ask the user to choose from the supported area keywords | Prompt routing and policy loading |
| R-ARCH-001 | Remote SaaS/API integrations use connectors plus outgoing APIs, connector workflow activities, or automation HTTP steps by default; do not model them as tools unless a local runtime/executable is required | Integration architecture and agent routing |
| R-CONN-001 | Google connector onboarding must begin from the Connect provider control and must not collect OAuth credentials through browser prompt dialogs | Connector onboarding UX and OAuth setup flows |
| R-CONN-002 | When adding a connector provider, also evaluate and define provider-aware prebuilt workflow activities in the connector activity catalog, including scopes, input schema, output schema, and execution mapping | Connector/provider implementation workflow |
| R-CONN-003 | Provider-aware connector workflow actions must use the connector activity system, remain provider-aware in the builder with explicit selectable UI actions plus action-specific inputs/outputs, and keep generic HTTP steps available for raw/custom API calls | Automation builder connector actions |
| R-DB-001 | Schema source of truth is `backend/database.py` | Database changes |
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
| R-TEST-002 | Use the two-tier test workflow: `scripts/test-precommit.sh` for fast local iteration and `scripts/test-full.sh` as the completion gate for user-visible workflow changes, shared frontend/test infrastructure changes, and browser coverage validation | Testing workflow changes |
| R-TEST-003 | Keep internal API smoke coverage in `tests/test_api_smoke_matrix.py` aligned with every served `/api/v1/**` route and `/health`, with cases sourced from `tests/api_smoke_registry/` | Backend route additions and removals |
| R-TEST-004 | Remove or retire a test only when the covered contract is removed or replaced, and update the replacement coverage in the same task | Test maintenance |
| R-TEST-005 | Any user-visible UI workflow change must add or update Playwright coverage in `ui/e2e/` unless the change is strictly non-behavioral | Frontend and browser workflow changes |
| R-TEST-006 | Playwright coverage must assert the changed workflow behavior, not only route load or static render | Playwright authoring and UI changes |
| R-TEST-007 | For startup, server-launch, or Playwright execution failures, verify what is already running by checking active listeners/processes on expected ports before treating the failure as unresolved | Failure recovery and test infrastructure troubleshooting |
| R-TEST-008 | Behavior-changing implementation work must add or update relevant automated tests in the same change unless the change is strictly non-behavioral | All implementation workflows |

<!-- MACHINE_INDEX_START
{
  "version": 18,
  "prompt_prefix": {
    "convention": "[AREA: <keyword>] <task description>",
    "routing_section": "#entry-point-routing",
    "keywords": ["db", "ui", "tools", "api", "test", "automation", "nav", "scripts"],
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
    "tool_catalog": ["backend/tool_registry.py"],
    "tool_manifest_generator": ["scripts/generate-tools-manifest.mjs"],
    "api_smoke_registry": ["tests/api_smoke_registry/", "tests/test_api_smoke_matrix.py"]
  },
  "task_routes": {
    "db_schema_change": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["backend/database.py"],
      "verify": ["tests/"]
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
      "edit": ["pytest.ini", "scripts/test-precommit.sh", "scripts/test-full.sh", "tests/api_smoke_registry/", "tests/test_api_smoke_matrix.py", "ui/e2e/", "ui/e2e/README.md"],
      "verify": ["pytest", "npm run test", "npm run build", "npm run test:e2e"]
    },
    "response_policy_update": {
      "read": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "edit": ["AGENTS.md", "backend/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md"],
      "check": ["#required-output-for-development-work", "#response-scope-and-instruction-fidelity", "#rules-matrix", "MACHINE_INDEX_START"],
      "verify": ["policy text and machine index stay synchronized"]
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
  }
}
MACHINE_INDEX_END -->

---

## Practical Do And Do Not Rules {#practical-do-and-do-not-rules}

Do:

- follow the existing DB-backed tool flow
- keep page entrypoints matched to page paths
- keep shared shell config centralized
- place tests beside the backend feature area they cover or under the React feature they cover
- add or update relevant automated tests in the same change when behavior changes
- prefer additive schema evolution over one-off DB edits

Do not:

- create a second source of truth for tools, routes, or settings
- put new page-entry logic into random root-level script files
- hardcode navigation that belongs to the shell
- edit `ui/dist/` directly
- assume `backend/main.py` is the place for new HTML routes
