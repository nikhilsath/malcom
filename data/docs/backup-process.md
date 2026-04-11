---
title: Backup process
slug: backup-process
summary: Describes how Malcom creates, stores, lists, and restores local PostgreSQL backups used by the Settings UI and APIs.
tags:
  - article-type/how-to
  - area/operations
  - workflow/backup
  - audience/operator
  - verification-date/2026-04-05
created_by_agent: fact-doc-writer
updated_by_agent: fact-doc-writer
created_at: 2026-04-05T12:00:00Z
updated_at: 2026-04-05T12:20:00Z
---

This document describes the local backup and restore process for Malcom's PostgreSQL-backed settings data and the operator workflows and developer references needed to create, list, and restore local dumps.

<details>
<summary>Article metadata</summary>

- **title:** Backup process
- **slug:** backup-process
- **summary:** Describes how Malcom creates, stores, lists, and restores local PostgreSQL backups used by the Settings UI and APIs.
- **tags:** article-type/how-to, area/operations, workflow/backup, audience/operator
- **created_at:** 2026-04-05T12:00:00Z
- **updated_at:** 2026-04-05T12:20:00Z
- **created_by_agent / updated_by_agent:** fact-doc-writer

</details>

## Table of Contents

- [Scope](#scope)
- [Prerequisites](#prerequisites)
- [Operator workflows](#operator-workflows)
  - [Create a backup (UI / API)](#create-a-backup-ui--api)
  - [List backups](#list-backups)
  - [Restore a backup (UI / API)](#restore-a-backup-ui--api)
- [Developer reference](#developer-reference)
  - [Related functions](#related-functions)
  - [Related tests](#related-tests)
- [Expected result](#expected-result)
- [Sources](#sources)

## Scope

Covers local, workspace-hosted PostgreSQL dumps created by the Settings Data backup actions.

Out of scope: remote or offsite backups (cloud snapshots, S3, managed provider backups).

## Prerequisites

- PostgreSQL client binaries (`pg_dump`, `pg_restore`) must be installed and available on `PATH` on the host performing the action.
- A PostgreSQL connection string must be available either via the `MALCOM_DATABASE_URL` environment variable or returned by `backend.database.get_database_url()` in the running application.

## Operator workflows

The following table pairs the user-facing interaction (left) with the program actions and functions invoked (right).

| User interaction | Program actions |
|---|---|
| `POST /api/v1/settings/data/backups` (Create backup via UI) | `create_backup()` resolves DB URL, ensures `data/backups/` exists, runs `pg_dump --format=custom --file <out_path> --dbname <db_url>`, returns metadata (`filename`, `path`, `created_at`, `size_bytes`). |
| `GET /api/v1/settings/data/backups` (List backups in UI) | `list_backups()` enumerates `*.dump` files in `data/backups/`, reads `stat()` for size/mtime, returns sorted metadata array. |
| `POST /api/v1/settings/data/backups/restore` (Restore selected backup) | `restore_backup(filename)` verifies file exists, resolves DB URL, runs `pg_restore --dbname <db_url> --clean --if-exists <path>`, returns `restored_at` and `stdout`/`stderr`. |

**Notes:** operator playbooks (manual shell restores) were removed — the product exposes create/list/restore via APIs and the UI for simple operations.

## Developer reference

Implementation details and locations for engineers.

### Related functions

| File | Purpose |
|---|---|
| `backend/services/settings_backup_restore.py` | Implements `create_backup()`, `list_backups()`, and `restore_backup()` using `pg_dump`/`pg_restore` and `data/backups/` as storage. |
| `backend/services/support.py` | Re-exports helpers for use by route handlers and higher-level services. |
| `tests/test_settings_api.py` | Tests that mock backup helpers and exercise API flows for create/list/restore. |

Refer to these files for implementation and unit-test behavior.

### Related tests

- `tests/test_settings_api.py` — API-level tests that mock backup helper functions to exercise create, list, and restore flows.


## Expected result

- Successful create: returns `filename`, `path`, `created_at` (UTC ISO8601 +Z), and `size_bytes`.
- Successful list: array of backup metadata, newest first.
- Successful restore: returns `restored_at` (UTC ISO8601 +Z) and `stdout`/`stderr` from `pg_restore`.

These behaviors are validated by unit tests that exercise the API surface (see `tests/test_settings_api.py`).

## Sources

- Implementation: [backend/services/settings_backup_restore.py](backend/services/settings_backup_restore.py)
- Support exports: [backend/services/support.py](backend/services/support.py)
- Settings API endpoints used by the UI: [data/docs/settings-reference.md](data/docs/settings-reference.md#L78)
- Tests that exercise backup API flows (mocked): [tests/test_settings_api.py](tests/test_settings_api.py#L287-L305)

