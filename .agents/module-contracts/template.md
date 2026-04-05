# Module Contract: `<module-name>`

> Copy this template to `.agents/module-contracts/<module-name>.md` and fill in every section.
> Sections marked **Required** must be completed before the module is merged.
> Sections marked **Optional** should be filled when applicable.

---

## Owner  *(Required)*

| Field        | Value                                      |
|--------------|--------------------------------------------|
| Team / Area  | `<backend \| ui \| tests \| infra>`        |
| Primary file | `<path/to/primary_module.py or .ts>`       |
| Introduced   | `<TASK-XXX or PR link>`                    |

---

## Responsibilities  *(Required)*

> One paragraph. What does this module do? What does it **not** do?

```
<Describe the single, clearly-bounded concern this module owns.>
```

---

## Public API  *(Required)*

> List every function, class, or hook that callers outside this module may use.
> Anything not listed here is considered private and may change without notice.

| Symbol | Signature / Props | Description |
|--------|-------------------|-------------|
| `<FunctionOrClass>` | `(param: Type) -> ReturnType` | What it does |
| `<ReactHookOrComponent>` | `{ prop: Type }` | What it renders/returns |

---

## Owned Database Tables  *(Required — write `none` if not applicable)*

> List every DB table (or SQLite schema segment) that this module owns.
> "Owns" means: it holds the CREATE TABLE, runs migrations, and is the sole writer.

| Table name | Schema file / migration | Notes |
|------------|------------------------|-------|
| `<table_name>` | `backend/database.py` or `alembic/versions/xxx.py` | |

---

## Inbound Dependencies  *(Required)*

> Modules / packages that **this module imports from**.

| Dependency | Type (`internal \| stdlib \| third-party`) | Purpose |
|------------|--------------------------------------------|---------|
| `<module_path_or_package>` | internal | |

---

## Outbound Dependencies  *(Required)*

> Modules that **import from this module** (i.e. this module's callers).
> Update this list whenever a new caller is added.

| Caller | How it uses this module |
|--------|------------------------|
| `<path/to/caller.py>` | calls `<symbol>` |

---

## Allowed Callers  *(Required)*

> Explicit allowlist. Any caller NOT on this list must get a contract review before importing.

```
# Example entries:
backend/routes/connectors.py
ui/src/automation/app.tsx
```

---

## Test Obligations  *(Required)*

> Every exported symbol must have coverage in at least one of the test tiers below.

| Test tier | File glob / command | Coverage expectation |
|-----------|---------------------|----------------------|
| Unit      | `tests/unit/test_<module>.py` or `ui/src/**/__tests__/` | All public functions/hooks |
| Contract  | `tests/contract/test_<module>_contract.py` | All cross-module boundaries |
| E2E       | `ui/e2e/<module>.spec.ts` *(UI modules only)* | Happy-path user flows |

Run locally with:

```bash
scripts/test-module.sh <module-name>
```

---

## Migration Rules  *(Required — write `none` if not applicable)*

> Rules that govern schema or data migrations owned by this module.

1. All schema changes must be made via an Alembic migration (or the project's equivalent).
2. Migrations must be reviewed in the same PR as the contract update.
3. Breaking schema changes (column rename, type change, removal) require a two-phase migration:
   - Phase 1: add new column / backfill.
   - Phase 2: remove old column after all callers are updated.
4. `<Any module-specific migration constraints.>`

---

## Refactor Constraints  *(Optional)*

> Conditions that must hold before AND after any refactor touching this module.

- [ ] Public API symbols are not renamed without a deprecation alias.
- [ ] Owned DB tables are not mutated outside of migrations.
- [ ] All callers listed in **Allowed Callers** still compile/type-check after changes.
- [ ] `<Any module-specific constraints.>`

---

## Change Log  *(Optional)*

| Date | Change | Task/PR |
|------|--------|---------|
| YYYY-MM-DD | Initial contract | `TASK-XXX` |
