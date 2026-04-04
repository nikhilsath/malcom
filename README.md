# Malcom

Malcom is a self-hosted, local-first automation orchestration platform for running workflows, APIs, connectors, and runtime-managed tools on your own machine or network.

It combines a FastAPI backend, PostgreSQL persistence, and a Vite-built, registry-driven multi-page web UI with both React/TypeScript and vanilla JavaScript pages.

## Table of Contents

- [What Malcom Does](#what-malcom-does)
- [UI Surface](#ui-surface)
- [Current Architecture](#current-architecture)
- [Database Schema](#database-schema)
- [Repository Map](#repository-map)
- [Quick Start](#quick-start)
- [Testing Workflow](#testing-workflow)
- [UI and Route Wiring](#ui-and-route-wiring)
- [Connectors vs Tools](#connectors-vs-tools)
- [Data Lineage Reference](#data-lineage-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## What Malcom Does

Malcom provides the API, UI, and runtime needed to build and operate local-first automation workflows.

It includes:

- a FastAPI API for automations, runs, inbound and outgoing APIs, webhooks, connectors, tools, scripts, settings, log tables, workers, and runtime status
- a browser UI for dashboard monitoring, automation authoring, API management, tools, scripts, connectors, and workspace settings
- an in-process scheduler, trigger queue, and worker coordination runtime for executing and tracking automation runs, including inbound API and webhook-triggered flows
- connector-backed outbound requests, reusable HTTP presets, and provider-specific connector activities
- a PostgreSQL-backed tool and settings store that also feeds generated frontend manifest data
- persisted run history and per-step execution details in PostgreSQL

Primary goals:

1. Run reliably on low-power local hardware, letting "tools" be run on any other connected machine for more intense tasks.
2. Keep workflows local-first.
3. Stay extensible for connectors and runtime-managed tools.

## UI Surface

The current product UI is organized into these areas:

- Dashboard: a shared dashboard app with home, devices, logs, and queue views
- Automations: overview, library, builder, and log data
- APIs: registry, incoming, outgoing, and webhooks
- Tools: catalog plus configuration pages for the current runtime-managed tools
- Scripts: reusable script library
- Settings: workspace, logging, notifications, access, connectors, and data

## Dashboard Data Sources

- Runtime telemetry: `runtime_resource_snapshots` and `/api/v1/dashboard/resource-dashboard`
- Dashboard logs (`/api/v1/dashboard/logs`) are backend-backed and sourced from application runtime log files.
- Resource dashboard cards and widgets are derived from persisted runtime snapshots rather than the in-memory debug resource profile.
- Resource profile (`/api/v1/debug/resource-profile`) remains available as a debug-only live metrics surface.

## Current Architecture

### Backend

- FastAPI app serving feature routers under `/api/v1/**`, `/health`, and the built UI/static surface
- Runtime scheduler, trigger queue, worker registration/claim flow, and automation execution services
- Feature APIs for automations, runs, inbound and outgoing APIs, webhooks, connectors, tools, scripts, log tables, settings, workers, dashboard status, runtime status, scheduler jobs, and trigger history
- Registry-driven served and redirect UI route registration via `backend/page_registry.py` and `ui/page-registry.json`

### Frontend

- Vite-built HTML entry pages and route metadata driven by `ui/page-registry.json`
- Mixed stack: React/TypeScript pages for dashboard and automations, plus vanilla JavaScript pages for APIs, settings, tools, and shell wiring

## Database Schema

Schema source of truth: `backend/database.py`

### API Registry

#### `inbound_apis`

Inbound API endpoint definitions for request-triggered automation entry points.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the inbound API definition. |
| `name` | `text` | Human-readable inbound API name. |
| `description` | `text` | Optional description shown in the UI. |
| `path_slug` | `text` | Unique slug used in the inbound API route. |
| `auth_type` | `text` | Authentication mode required for requests. |
| `secret_hash` | `text` | Stored hash for the inbound API secret. |
| `is_mock` | `integer` | `0`/`1` flag indicating mock/test mode. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the inbound API is active. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `inbound_api_events`

Inbound API request history tied to `inbound_apis`.

| Column | Type | Meaning |
|---|---|---|
| `event_id` | `text` | Primary key for the received inbound API event. |
| `api_id` | `text` | Foreign key to [`inbound_apis`](#inbound_apis)`.`id`. |
| `received_at` | `text` | Timestamp when the request arrived. |
| `status` | `text` | Result of inbound request processing. |
| `request_headers_subset` | `text` | JSON text containing the stored subset of request headers. |
| `payload_json` | `text` | Optional JSON text payload body. |
| `source_ip` | `text` | Optional client IP captured for the request. |
| `error_message` | `text` | Optional processing error detail. |
| `is_mock` | `integer` | `0`/`1` flag indicating a mock/test event. |

#### `outgoing_scheduled_apis`

Scheduled outbound API definitions for cron-like or time-based deliveries.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the outbound scheduled API definition. |
| `name` | `text` | Human-readable outbound API name. |
| `description` | `text` | Optional description shown in the UI. |
| `path_slug` | `text` | Unique slug for the saved outbound API resource. |
| `is_mock` | `integer` | `0`/`1` flag indicating mock/test mode. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the resource is active. |
| `status` | `text` | Current schedule status such as `active` or `paused`. |
| `repeat_enabled` | `integer` | `0`/`1` flag controlling repeat scheduling. |
| `destination_url` | `text` | Fully resolved outbound destination URL. |
| `http_method` | `text` | HTTP method used for delivery. |
| `auth_type` | `text` | Auth mode used when sending the request. |
| `auth_config_json` | `text` | JSON text for inline outbound auth settings. |
| `webhook_signing_json` | `text` | JSON text for optional outbound signing headers/verification config. |
| `payload_template` | `text` | Request payload template stored as text. |
| `scheduled_time` | `text` | Default clock time used for daily schedule execution. |
| `schedule_expression` | `text` | Stored schedule expression for runtime scheduling. |
| `last_run_at` | `text` | Optional timestamp for the most recent delivery attempt. |
| `next_run_at` | `text` | Optional timestamp for the next queued delivery. |
| `last_error` | `text` | Optional last delivery failure summary. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `outgoing_continuous_apis`

Continuously repeating outbound API definitions with interval-based delivery.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the continuous outbound API definition. |
| `name` | `text` | Human-readable outbound API name. |
| `description` | `text` | Optional description shown in the UI. |
| `path_slug` | `text` | Unique slug for the saved outbound API resource. |
| `is_mock` | `integer` | `0`/`1` flag indicating mock/test mode. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the resource is active. |
| `repeat_enabled` | `integer` | `0`/`1` flag controlling repeat delivery. |
| `repeat_interval_minutes` | `integer` | Optional repeat interval in minutes. |
| `destination_url` | `text` | Fully resolved outbound destination URL. |
| `http_method` | `text` | HTTP method used for delivery. |
| `auth_type` | `text` | Auth mode used when sending the request. |
| `auth_config_json` | `text` | JSON text for inline outbound auth settings. |
| `webhook_signing_json` | `text` | JSON text for optional outbound signing headers/verification config. |
| `payload_template` | `text` | Request payload template stored as text. |
| `stream_mode` | `text` | Stored mode label for the continuous resource. |
| `last_run_at` | `text` | Optional timestamp for the most recent delivery attempt. |
| `next_run_at` | `text` | Optional timestamp for the next queued delivery. |
| `last_error` | `text` | Optional last delivery failure summary. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `webhook_apis`

Webhook receiver definitions used for event-driven inbound integrations.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the webhook definition. |
| `name` | `text` | Human-readable webhook name. |
| `description` | `text` | Optional description shown in the UI. |
| `path_slug` | `text` | Unique slug for the webhook. |
| `is_mock` | `integer` | `0`/`1` flag indicating mock/test mode. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the webhook is active. |
| `delivery_mode` | `text` | Stored mode label for the resource. Current live data uses `webhook`. |
| `callback_path` | `text` | Receive path served by the webhook endpoint. |
| `verification_token` | `text` | Shared verification token used during webhook validation. |
| `signing_secret` | `text` | Secret used for HMAC signature validation. |
| `signature_header` | `text` | Header name expected to carry the webhook signature. |
| `event_filter` | `text` | Optional event-name filter applied before automation triggering. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `webhook_api_events`

Webhook delivery history tied to `webhook_apis`.

| Column | Type | Meaning |
|---|---|---|
| `event_id` | `text` | Primary key for the received webhook event. |
| `api_id` | `text` | Foreign key to [`webhook_apis`](#webhook_apis)`.`id`. |
| `received_at` | `text` | Timestamp when the webhook arrived. |
| `status` | `text` | Result of webhook processing. |
| `event_name` | `text` | Optional event name extracted from the payload/headers. |
| `verification_ok` | `integer` | `0`/`1` flag showing whether token verification succeeded. |
| `signature_ok` | `integer` | `0`/`1` flag showing whether signature verification succeeded. |
| `request_headers_subset` | `text` | JSON text containing the stored subset of request headers. |
| `payload_json` | `text` | Optional JSON text payload body. |
| `raw_body` | `text` | Optional raw request body string. |
| `source_ip` | `text` | Optional client IP captured for the request. |
| `error_message` | `text` | Optional processing error detail. |
| `triggered_automation_count` | `integer` | Number of automations triggered by the event. |
| `is_mock` | `integer` | `0`/`1` flag indicating a mock/test event. |

#### `outgoing_delivery_history`

Delivery attempt history for outbound API resources and outbound automation HTTP steps.

| Column | Type | Meaning |
|---|---|---|
| `delivery_id` | `text` | Primary key for the delivery history row. |
| `resource_type` | `text` | Polymorphic source type such as `outgoing_scheduled` or `automation_http_step`. |
| `resource_id` | `text` | Source record identifier for the delivery. |
| `status` | `text` | Delivery result status. |
| `http_status_code` | `integer` | Optional HTTP response code. |
| `request_summary` | `text` | Optional request summary captured for logs/UI. |
| `response_summary` | `text` | Optional response summary captured for logs/UI. |
| `error_summary` | `text` | Optional error summary captured for failures. |
| `started_at` | `text` | Timestamp when the request started. |
| `finished_at` | `text` | Optional timestamp when the request finished. |

#### `runtime_resource_snapshots`

Persisted runtime telemetry snapshots used by dashboard resource history and the resource dashboard summary/widgets.

| Column | Type | Meaning |
|---|---|---|
| `snapshot_id` | `text` | Primary key for the telemetry snapshot row. |
| `captured_at` | `text` | Timestamp when the snapshot was captured. |
| `process_memory_mb` | `real` | Best-effort runtime process RSS memory at capture time. |
| `process_cpu_percent` | `real` | Best-effort runtime process CPU percentage at capture time. |
| `queue_pending_jobs` | `integer` | Number of pending runtime trigger jobs when captured. |
| `queue_claimed_jobs` | `integer` | Number of claimed runtime trigger jobs when captured. |
| `tracked_operations` | `integer` | Number of currently tracked in-memory resource metrics. |
| `total_error_count` | `integer` | Aggregate error count across tracked operations at capture time. |
| `hottest_operation` | `text` | Operation name with the highest total latency when captured. |
| `hottest_total_duration_ms` | `real` | Total latency for the hottest operation at capture time. |
| `max_memory_peak_mb` | `real` | Highest operation-level memory peak observed in tracked metrics at capture time. |
| `total_storage_used_bytes` | `integer` | Aggregate used bytes across detected storage devices at capture time. |
| `total_storage_capacity_bytes` | `integer` | Aggregate storage capacity across detected storage devices at capture time. |
| `total_storage_usage_percent` | `real` | Aggregate storage usage percentage across detected storage devices at capture time. |
| `local_storage_used_bytes` | `integer` | Used bytes on the primary local runtime volume. |
| `local_storage_capacity_bytes` | `integer` | Total bytes on the primary local runtime volume. |
| `local_storage_usage_percent` | `real` | Usage percentage on the primary local runtime volume. |
| `disk_read_bytes` | `integer` | Cumulative disk read bytes captured from the host at snapshot time. |
| `disk_write_bytes` | `integer` | Cumulative disk write bytes captured from the host at snapshot time. |
| `network_sent_bytes` | `integer` | Cumulative network bytes sent captured from the host at snapshot time. |
| `network_received_bytes` | `integer` | Cumulative network bytes received captured from the host at snapshot time. |
| `top_processes_json` | `text` | JSON text array of the top memory-consuming processes captured with pid, name, memory MB, and memory percent. |

### Workspace State

#### `tools`

Persisted tool catalog metadata. This stores seeded tool definitions plus user overrides and authoritative enablement state.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key and stable tool identifier. |
| `source_name` | `text` | Canonical tool name seeded from the backend catalog. |
| `source_description` | `text` | Canonical tool description seeded from the backend catalog. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the tool is enabled. |
| `name_override` | `text` | Optional user override for the tool display name. |
| `description_override` | `text` | Optional user override for the tool description. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |
| `inputs_schema_json` | `text` | JSON text describing workflow-step input fields for the tool. |
| `outputs_schema_json` | `text` | JSON text describing workflow-step output fields for the tool. |

#### `tool_configs`

Managed tool runtime configuration blobs keyed by `tool_id`. This stores per-tool runtime settings such as SMTP listener details or local LLM endpoint configuration, without duplicating enabled state.

| Column | Type | Meaning |
|---|---|---|
| `tool_id` | `text` | Primary key referencing [`tools`](#tools)`.`id`. |
| `config_json` | `text` | JSON text payload for the tool's runtime configuration. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `settings`

Named JSON settings sections for workspace-level app configuration.

| Column | Type | Meaning |
|---|---|---|
| `key` | `text` | Primary key for the settings section name. |
| `value_json` | `text` | JSON text payload for the settings section. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `integration_presets`

Provider-preset catalog for connectors. This is the intended authoritative store for provider metadata shown in connector setup flows.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key and canonical provider identifier such as `google` or `github`. |
| `integration_type` | `text` | Preset type discriminator. Current provider catalog rows use `connector_provider`. |
| `name` | `text` | Human-readable provider name. |
| `description` | `text` | Provider description shown in setup flows. |
| `category` | `text` | Catalog grouping used for provider organization. |
| `auth_types_json` | `text` | JSON text array of supported auth types for the provider. |
| `default_scopes_json` | `text` | JSON text array of default OAuth scopes for the provider. |
| `docs_url` | `text` | Provider documentation URL. |
| `base_url` | `text` | Default provider API base URL. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `connectors`

Saved connector instance records. The active connector read/write path uses instance columns such as `provider`, `status`, `auth_type`, `scopes_json`, `credential_ref`, and `auth_config_json`.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the saved connector instance. |
| `provider` | `text` | Canonical provider id for the connector instance. |
| `name` | `text` | Display name for the connector. |
| `status` | `text` | Connector auth/runtime status such as `draft`, `connected`, or `revoked`. |
| `auth_type` | `text` | Selected auth strategy for the connector instance. |
| `scopes_json` | `text` | JSON text array of granted/requested scopes for the connector instance. |
| `base_url` | `text` | Base API URL for the connector/provider. |
| `owner` | `text` | Human-readable owner label. |
| `docs_url` | `text` | Provider docs URL or connector docs reference. |
| `credential_ref` | `text` | Secret-storage reference for the connector. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |
| `auth_config_json` | `text` | JSON text for protected auth configuration and stored credential metadata. |
| `last_tested_at` | `text` | Optional timestamp of the last credential test/check. |

#### `connector_auth_policies`

Workspace-level connector credential policy storage. This keeps auth-policy settings in a dedicated table rather than mixing them into app settings sections.

| Column | Type | Meaning |
|---|---|---|
| `policy_id` | `text` | Primary key for the singleton workspace policy row. |
| `auth_policy_json` | `text` | JSON text payload for connector auth policy settings. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `connector_endpoint_definitions`

Provider-aware endpoint/action catalog for connector activities, HTTP presets, and OAuth endpoint flows.

| Column | Type | Meaning |
|---|---|---|
| `endpoint_id` | `text` | Primary key and stable endpoint/action identifier. |
| `provider_id` | `text` | Provider id owning the endpoint definition. This references `integration_presets.id`. |
| `endpoint_kind` | `text` | Kind of definition such as `activity`, `http_preset`, or OAuth endpoint type. |
| `service` | `text` | Provider sub-service grouping such as `gmail`, `drive`, or `oauth`. |
| `operation_type` | `text` | Action verb or semantic operation category. |
| `label` | `text` | Human-readable label shown in UI flows. |
| `description` | `text` | Human-readable description of the endpoint/action. |
| `http_method` | `text` | HTTP method used for the request. |
| `endpoint_path_template` | `text` | Path template relative to the provider base URL. |
| `query_params_json` | `text` | JSON text of static query parameters/defaults owned by the endpoint definition. |
| `required_scopes_json` | `text` | JSON text array of scopes required for this endpoint/action. |
| `input_schema_json` | `text` | JSON text schema describing the user-editable inputs exposed by the builder. |
| `output_schema_json` | `text` | JSON text schema describing structured outputs returned by the action. |
| `payload_template` | `text` | Stored request-body template used by the action. |
| `execution_json` | `text` | JSON text mapping used by the runtime execution layer. |
| `metadata_json` | `text` | JSON text for extra endpoint metadata not modeled in first-class columns. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

### Automation Runtime

#### `automations`

Top-level automation definitions and trigger configuration.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the automation. |
| `name` | `text` | Human-readable automation name. |
| `description` | `text` | Optional automation description. |
| `enabled` | `integer` | `0`/`1` flag controlling whether the automation can run. |
| `trigger_type` | `text` | Trigger mode such as manual, schedule, inbound API, or webhook. |
| `trigger_config_json` | `text` | JSON text trigger configuration payload. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |
| `last_run_at` | `text` | Optional timestamp for the most recent completed run. |
| `next_run_at` | `text` | Optional timestamp for the next scheduled run. |
| `default_storage_location_id` | `text` | Optional default storage destination id for run artifacts. This points into storage settings, not a dedicated table. |

#### `automation_steps`

Ordered step definitions for each automation.

| Column | Type | Meaning |
|---|---|---|
| `step_id` | `text` | Primary key for the automation step definition. |
| `automation_id` | `text` | Foreign key to [`automations`](#automations)`.`id`. |
| `position` | `integer` | Ordered position within the automation; unique per automation. |
| `step_type` | `text` | Step kind such as tool, API, condition, or script. |
| `name` | `text` | Human-readable step name. |
| `config_json` | `text` | JSON text configuration payload for the step. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |
| `on_true_step_id` | `text` | Optional branch target step id used for condition true paths. |
| `on_false_step_id` | `text` | Optional branch target step id used for condition false paths. |
| `is_merge_target` | `integer` | `0`/`1` flag indicating the step is intended as a branch merge target. |

#### `automation_runs`

Execution-history rows for automation runs.

| Column | Type | Meaning |
|---|---|---|
| `run_id` | `text` | Primary key for the automation run. |
| `automation_id` | `text` | Parent automation id for the run. The live schema does not currently enforce this with a foreign key. |
| `trigger_type` | `text` | Trigger mode that started the run. |
| `status` | `text` | Run status such as queued, running, succeeded, or failed. |
| `worker_id` | `text` | Optional worker id assigned to the run. |
| `worker_name` | `text` | Optional worker display name recorded for the run. |
| `started_at` | `text` | Run start timestamp stored as ISO text. |
| `finished_at` | `text` | Optional run completion timestamp stored as ISO text. |
| `duration_ms` | `integer` | Optional computed run duration in milliseconds. |
| `error_summary` | `text` | Optional top-level error summary for failed runs. |

#### `automation_run_steps`

Per-step execution history for a run.

| Column | Type | Meaning |
|---|---|---|
| `step_id` | `text` | Primary key for the run-step history row. |
| `run_id` | `text` | Foreign key to [`automation_runs`](#automation_runs)`.`run_id`. |
| `step_name` | `text` | Step name snapshot recorded at execution time. |
| `status` | `text` | Step execution status. |
| `request_summary` | `text` | Optional request/input summary for the step. |
| `response_summary` | `text` | Optional response/output summary for the step. |
| `started_at` | `text` | Step start timestamp stored as ISO text. |
| `finished_at` | `text` | Optional step completion timestamp stored as ISO text. |
| `duration_ms` | `integer` | Optional computed duration in milliseconds. |
| `detail_json` | `text` | Optional JSON text with step-specific detail payloads. |
| `inputs_json` | `text` | JSON text snapshot of resolved step inputs. |
| `response_body_json` | `text` | Optional JSON text copy of parsed response bodies for supported step types. |
| `extracted_fields_json` | `text` | Optional JSON text of extracted response-mapping fields. |

#### `storage_artifacts`

Stored artifact metadata produced by automation steps. This table tracks logical artifact records; the actual file may live in a local folder or provider-backed destination.

| Column | Type | Meaning |
|---|---|---|
| `artifact_id` | `text` | Primary key for the artifact row. |
| `storage_location_id` | `text` | Logical storage location id. This references the storage settings payload, not a dedicated relational table. |
| `storage_kind` | `text` | Storage backend kind such as `local_folder` or `google_drive_folder`. |
| `byte_size` | `integer` | Artifact size in bytes. |
| `reference_key` | `text` | Local path or provider reference key for the stored artifact. |
| `automation_id` | `text` | Optional automation id that produced the artifact. |
| `run_id` | `text` | Optional run id that produced the artifact. |
| `step_id` | `text` | Optional step id that produced the artifact. |
| `provider_path` | `text` | Optional provider-native destination path/identifier. |
| `metadata_json` | `text` | JSON text with extra artifact metadata such as MIME type or display name. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `deleted_at` | `text` | Optional soft-delete timestamp. `NULL` means the artifact is active. |

### Script Library

#### `scripts`

Reusable script definitions stored in the library.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the script. |
| `name` | `text` | Human-readable script name. |
| `description` | `text` | Optional script description. |
| `language` | `text` | Script language/runtime identifier. |
| `code` | `text` | Stored script source code. |
| `validation_status` | `text` | Current validation state such as `unknown`, `valid`, or `invalid`. |
| `validation_message` | `text` | Optional validation error/warning detail. |
| `last_validated_at` | `text` | Optional timestamp of the last validation pass. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |
| `sample_input` | `text` | Stored sample input used for testing or authoring help. |

### Log Schema Metadata

`log_db_tables` and `log_db_columns` define dynamic `log_data_*` tables created at runtime for write-to-DB/log workflows. The metadata tables below are fixed; generated `log_data_*` tables are not listed here because their shape depends on user-created definitions.

#### `log_db_tables`

Managed metadata for user-defined log tables.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the managed log table definition. |
| `name` | `text` | Unique logical table name used to derive the physical `log_data_<name>` table. |
| `description` | `text` | Optional description of the table's purpose. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `log_db_columns`

Managed metadata for columns belonging to a `log_db_tables` definition.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the managed column definition. |
| `table_id` | `text` | Foreign key to [`log_db_tables`](#log_db_tables)`.`id`. |
| `column_name` | `text` | Column name that will be created on the physical `log_data_*` table. |
| `data_type` | `text` | Logical type selected for the managed column. |
| `nullable` | `integer` | `0`/`1` flag indicating whether the generated column allows `NULL`. |
| `default_value` | `text` | Optional literal default value applied to the generated column. |
| `position` | `integer` | Stable display/creation order for the column within the table definition. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |

#### `storage_locations`

Persisted storage destination rows. These are the runtime source of truth for local folders, Google Drive folders, and repo storage roots used by automation write steps.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the storage location. |
| `name` | `text` | Human-readable label for the location. |
| `location_type` | `text` | One of `local`, `google_drive`, or `repo`. |
| `path` | `text` | Local filesystem path (for `local`/`repo`) or Google Drive folder ID (for `google_drive`). |
| `connector_id` | `text` | Foreign key to `connectors.id`; required for `google_drive` type. |
| `folder_template` | `text` | Optional Jinja template for sub-folder naming, e.g. `{data_type}/{year}-{month}`. |
| `file_name_template` | `text` | Optional Jinja template for file naming, e.g. `{target}-{timestamp}`. |
| `max_size_mb` | `integer` | Per-location quota in megabytes. `NULL` means unlimited. |
| `is_default_logs` | `integer` | `0`/`1` flag: when `1` this location receives API event log output. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

#### `repo_checkouts`

Managed GitHub repo clones linked to a `storage_locations` row of type `repo`.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text` | Primary key for the checkout record. |
| `storage_location_id` | `text` | Foreign key to [`storage_locations`](#storage_locations)`.`id`. |
| `repo_url` | `text` | Remote repository URL used for clone/pull. |
| `local_path` | `text` | Absolute local path where the repo is checked out. |
| `branch` | `text` | Branch name to track (default `main`). |
| `last_synced_at` | `text` | Timestamp of the most recent successful clone/pull. |
| `size_bytes` | `integer` | Measured size of the checkout on disk in bytes after last sync. |
| `created_at` | `text` | Creation timestamp stored as ISO text. |
| `updated_at` | `text` | Last update timestamp stored as ISO text. |

### Schema Health Notes

The current schema is serviceable for a single-environment local-first app, but it is not fully aligned with stricter relational database best practices yet.

- Good: primary keys exist for every documented table, unique constraints exist where identity matters (`path_slug`, tool ids, managed log names), and key child tables such as `automation_steps`, `automation_run_steps`, `inbound_api_events`, `webhook_api_events`, and `log_db_columns` already use foreign keys.
- Good: connector source-of-truth is split cleanly by responsibility: `integration_presets` for provider catalog rows (seeded from [`DEFAULT_CONNECTOR_CATALOG`](backend/services/connectors.py) on init), `connectors` for saved connector instance rows, `connector_auth_policies` for workspace credential policy, and `connector_endpoint_definitions` for provider action/endpoint metadata. `get_stored_connector_settings()` assembles the response from those DB-backed sources, and legacy `settings.connectors` rows are only a startup migration input.
- Good: scheduler-heavy query paths now have dedicated composite indexes for the runtime lookups used by automations, outbound APIs, runs, and connectors.
- Needs improvement: most timestamps are stored as `text` instead of `timestamptz`, most booleans are stored as `integer` instead of `boolean`, and most structured payloads are stored as `text` instead of `jsonb`.
- Needs improvement: several important reference columns intentionally remain soft references today, including `automation_runs.automation_id`, `storage_artifacts.automation_id`, `storage_artifacts.run_id`, and `storage_artifacts.step_id`, because current deletion/retention behavior preserves historical records.

## Repository Map

### Core backend

- `backend/main.py` - app factory and mounting
- `backend/routes/` - feature API routers plus UI-serving glue
- `backend/page_registry.py` - UI page registry loader and validator
- `backend/runtime.py` - runtime event bus, queue, and worker state
- `backend/services/` - runtime and feature logic
- `backend/schemas/` - request/response contracts
- `backend/database.py` - schema initialization and additive evolution
- `backend/tool_registry.py` - seed tool catalog plus DB sync and manifest support

### Core frontend

- `ui/<section>/<page>.html` - page entry HTML
- `ui/page-registry.json` - canonical served and redirect UI page registry
- `ui/page-registry.ts` - Vite input generation from the page registry
- `ui/src/` - React/TS features for dashboard and automations, plus TypeScript modules such as the scripts library and shared frontend helpers
- `ui/scripts/` - vanilla page controllers plus shared shell logic for APIs, settings, and tools
- `ui/modals/` - shared modal HTML fragments loaded by vanilla UI pages
- `ui/styles/` - shared and page styles
- `ui/vite.config.ts` - Vite config using registry-derived inputs

### Tooling and tests

- `scripts/` - developer scripts and test runners
- `tests/` - backend tests, API coverage, and smoke registry/matrix support
- `ui/src/**/__tests__/` - frontend unit tests for React/TypeScript features
- `ui/e2e/` - Playwright workflow coverage

## Quick Start

### Prerequisites

- macOS or Linux shell
- Python 3.x
- Node.js + npm
- PostgreSQL reachable on `127.0.0.1:5432`

Notes:

- On macOS/Homebrew, `./malcom` can auto-start a Homebrew PostgreSQL service if PostgreSQL is not already responsive.
- On Linux or non-Homebrew setups, start PostgreSQL yourself before running `./malcom`.

### 1) Set database URL

```bash
export MALCOM_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/malcom"
```

If omitted, the app falls back to `postgresql://postgres:postgres@127.0.0.1:5432/malcom`.

Note:

- The FastAPI app reads `MALCOM_DATABASE_URL`.
- The `./malcom` launcher still checks for a PostgreSQL listener on `127.0.0.1:5432` before startup, regardless of that env var.

### 2) Start the app

```bash
./malcom
```

What this launcher does:

- creates and uses `./.venv` if needed
- re-execs into `./.venv`
- installs backend dependencies from `requirements.txt`
- installs UI dependencies with `npm ci` in `ui/`
- builds UI when inputs changed
- checks PostgreSQL responsiveness on `127.0.0.1:5432`
- attempts Homebrew PostgreSQL startup when needed on supported macOS setups
- starts Uvicorn with `--reload` on `127.0.0.1:8000`
- aborts if port `8000` is already occupied

### 3) Open the app

- UI and API host: `http://127.0.0.1:8000`

### Settings Data local backups

- Settings -> Data includes a Local backups section for creating and restoring PostgreSQL dumps from the current workspace database.
- Backup creation and restore use `pg_dump` and `pg_restore` against `MALCOM_DATABASE_URL`.
- Backup files are stored locally under `backend/data/backups/` in the repository workspace on the machine running Malcom.
- If PostgreSQL client binaries are missing from `PATH`, the Settings Data backup actions return an inline error instead of silently failing.

## Testing Workflow

Malcom uses a two-tier test workflow.

Before running the test scripts:

- Run `./malcom` once first, or otherwise create `./.venv`, install `requirements.txt`, and install `ui/` dependencies.
- Set `MALCOM_TEST_DATABASE_URL` to a dedicated PostgreSQL database.
- If `MALCOM_TEST_DATABASE_URL` is unset, tests fall back to `MALCOM_DATABASE_URL`, then `postgresql://postgres:postgres@127.0.0.1:5432/malcom_test`.

Important:

- Playwright and test reset helpers truncate core tables and drop dynamic log data tables in the resolved test database.
- Do not point `MALCOM_TEST_DATABASE_URL` or fallback values at a database you want to keep.

### Fast local iteration

```bash
./scripts/test-precommit.sh
```

Runs:

- PostgreSQL test DB preflight and schema initialization
- backend pytest suite excluding smoke marker (`-m "not smoke"`)
  - includes UI registry/source file contract coverage in `tests/test_ui_html_routes.py` (every served `ui/page-registry.json` page must map to an existing `ui/*.html` source file)
- UI entry wiring check (`node scripts/check-ui-page-entry-modules.mjs`)
- Playwright served-route coverage map validation (`npm --prefix ui run test:e2e:coverage`)
- frontend unit tests (`npm test` in `ui/`)
- frontend build (`npm run build` in `ui/`)

### Full completion gate

```bash
bash ./scripts/test-full.sh
```

Runs:

- everything from `test-precommit.sh`
- smoke matrix (`pytest tests/test_api_smoke_matrix.py -m smoke`)
- external probe report (`python scripts/test-external-probes.py`)
- Playwright workflows (`npm run test:e2e` in `ui/`)

Playwright details:

- Launches its own app server through `scripts/run_playwright_server.sh`
- Resets the test database before startup
- Uses `MALCOM_TEST_DATABASE_URL` when set, otherwise falls back to `MALCOM_DATABASE_URL`, then `malcom_test`
- Validates `ui/e2e/coverage-route-map.json` against `ui/page-registry.json` before broad browser execution

Targeted browser iteration:

```bash
cd ui && npx playwright test <spec>
```

Route ownership validation:

```bash
cd ui && npm run test:e2e:coverage
```

Before using the targeted Playwright command:

- install browser binaries once with `cd ui && npm run test:e2e:install`
- make sure built UI assets already exist, for example by running `./malcom` once or `cd ui && npm run build`

### Test policy

- Behavior-changing implementation work must add or update relevant automated tests in the same change.
- User-visible workflow changes require Playwright coverage updates unless strictly non-behavioral.
- Playwright test retirement is replacement-first: update `ui/e2e/coverage-route-map.json` with replacement spec ownership before deleting older route coverage.
- API route additions/removals must stay aligned with `tests/test_api_smoke_matrix.py` and `tests/api_smoke_registry/`.

## UI and Route Wiring

For a new served UI page to work end-to-end:

1. Add `ui/<section>/<page>.html`.
2. Wire the page entry in the HTML itself:
   - React pages load `ui/src/<feature>/main.tsx` or `main.ts`.
   - Vanilla pages load `ui/scripts/<section>/<page>.js`.
3. Add the route record to `ui/page-registry.json`, including `serveMode`, legacy aliases, and redirect target when needed.
4. Build UI with `cd ui && npm run build`.

Notes:

- Do not hand-edit `ui/dist/**`.
- Vite inputs and backend-served UI routes derive from the page registry.
- The registry supports canonical served pages, redirect-only routes, and legacy aliases.
- Page entry modules are checked by `scripts/check-ui-page-entry-modules.mjs`; new page wiring should stay within the page's section instead of adding arbitrary new root-level entry files.
- Shared shell pages should use `id="topnav"`, `id="sidenav"`, `data-section`, and usually `data-sidenav-item` plus `data-shell-path-prefix`.
- Dashboard subpages are routed as redirects into the main dashboard entry with hash-based subroutes.
- The Tools section combines static catalog navigation with manifest-driven tool entries; enabled state filters the shell nav, while tool page routes still come from the page registry.

## Connectors vs Tools

Use the right integration model:

- **Connectors**: saved provider auth, base URL, scopes, and reusable remote API settings (Google, GitHub, etc.).
- **Outgoing APIs / HTTP steps**: request definitions for raw or custom remote API calls, including connector-scoped preset-driven requests in automation steps.
- **Connector activities**: provider-aware automation actions with explicit inputs, outputs, and required scopes.
- **Tools**: local or worker-bound machine capabilities exposed through the managed tool catalog (for example SMTP, local LLM, Coqui TTS, and Image Magic).

Rule of thumb:

- Remote SaaS/API access belongs in connectors plus outgoing APIs, automation HTTP steps, or provider-aware connector activities.
- Use connector activities for common provider actions in the automation builder; keep generic HTTP steps for raw or custom calls.
- Do not model remote API calls as tools unless local runtime execution or worker-bound machine behavior is required.

Connector onboarding behavior:

- Start first-party connector setup from the provider's `Connect` control on the Connectors page.
- Google, Notion, and Trello use guided OAuth setup with provider-specific client credentials, redirect handling, status copy, and callback completion.
- GitHub uses PAT-based onboarding. Save a personal access token directly from the Connectors page, select the required scopes from the multi-select list, then run Check connection.
- Notion OAuth requires a client secret for exchange, refresh, and revoke. It can read `MALCOM_NOTION_OAUTH_CLIENT_ID` and `MALCOM_NOTION_OAUTH_CLIENT_SECRET` when the setup form omits them; the Notion integration redirect URI should point to `/api/v1/connectors/notion/oauth/callback`.
- Trello OAuth can read `MALCOM_TRELLO_OAUTH_CLIENT_ID` and `MALCOM_TRELLO_OAUTH_CLIENT_SECRET` when the setup form omits them; the default callback path is `/api/v1/connectors/trello/oauth/callback`.
  Trello does not provide long-lived refresh tokens in the current connector contract; refresh attempts will return `409` and must be handled by reconnecting the provider.
- Google and GitHub both expose deeper workflow-builder catalogs with provider-aware connector actions and reusable HTTP presets across their major service areas.
- Notion and Trello onboarding currently stops at saved connector setup and generic API usage. They do not yet ship provider-specific connector activities or HTTP presets in the workflow builder.
- Do not collect OAuth credentials via browser `prompt()` dialogs.

### Workflow builder connector option source of truth

Connector options shown in the automation builder are resolved through one backend path:

1. Persisted connector records are stored in the `connectors` table.
2. `backend/services/workflow_builder.py:list_workflow_builder_connectors` normalizes provider IDs and enriches provider display metadata.
3. `GET /api/v1/automations/workflow-connectors` in `backend/routes/automations.py` returns the normalized option list.
4. `ui/src/automation/builder-api.ts:loadBuilderSupportData` loads that endpoint, and `ui/src/automation/useAutomationBuilderController.ts` passes the normalized options to HTTP and connector-activity step forms.

This flow is authoritative for builder connector availability. Do not add parallel hardcoded connector option lists in UI components.

## Data Lineage Reference

Updated by TASK-003 based on verified implementation.

Maps frontend components → API endpoints → backend services → database tables for all dynamic data flows.

Use this reference to understand data dependencies and trace where UI data originates in the database. Each entry documents the complete lineage from frontend element through the backend to persistent storage.

### Automation Builder Data Sources

The automation builder loads all dynamic data via `ui/src/automation/builder-api.ts:loadBuilderSupportData()`, which is consumed by `ui/src/automation/useAutomationBuilderController.ts` and fetches its support data in parallel:

#### Saved Connectors

Verified implementation notes (TASK-003):

- Canvas mode and guided mode share the same saved-connector path through `ui/src/automation/useAutomationBuilderController.ts` and `ui/src/automation/step-modals/connector-activity-step-form.tsx`.
- Frontend request path remains `GET /api/v1/automations/workflow-connectors`.
- Backend normalization path remains `backend/routes/automations.py:list_workflow_builder_connectors_endpoint` -> `backend/services/workflow_builder.py:list_workflow_builder_connectors`.
- Persistence source remains `connectors` (instance rows) with provider metadata enrichment from `integration_presets` where available.
- UI states now include loading, empty, error-with-retry, and incompatible-disabled connector options with inline reason text/title tooltips.

Expected saved-connector payload shape (normalized):

| Field | Meaning |
|---|---|
| `id` | Saved connector id from `connectors.id` |
| `name` | Display name from `connectors.name` |
| `provider` | Canonical provider id |
| `provider_name` | Human-readable provider label |
| `status` | Connector status string |
| `auth_type` | Connector auth type |
| `scopes` | Granted/requested scope list |
| `owner` | Optional owner label |
| `base_url` | Optional provider base URL |
| `docs_url` | Optional docs URL |
| `created_at` | Creation timestamp |
| `updated_at` | Last update timestamp |
| `last_tested_at` | Optional health-check timestamp |
| `source_path` | Normalized source marker (`connectors`) |

Deprecated/inaccurate path note:

- Do not source builder connector availability from cached frontend settings payloads or page-level globals; use only `GET /api/v1/automations/workflow-connectors`.
- Do not add duplicate connector option lists in UI components when backend resolver output exists.

Maintainer update points for this lineage:

- Backend normalization logic: `backend/services/workflow_builder.py:list_workflow_builder_connectors`
- API contract/model: `backend/schemas/automation.py:WorkflowBuilderConnectorOptionResponse`
- API route wiring: `backend/routes/automations.py:list_workflow_builder_connectors_endpoint`
- UI consumer wiring: `ui/src/automation/builder-api.ts:loadBuilderSupportData`

| Component | Path |
|---|---|
| **Frontend component** | `ui/src/automation/step-modals/connector-activity-step-form.tsx` |
| **HTML element** | `#add-step-connector-activity-connector-input` (`<select>`)  |
| **API endpoint** | `GET /api/v1/automations/workflow-connectors` |
| **Backend route handler** | `backend/routes/automations.py:list_workflow_builder_connectors_endpoint()` (line 44) |
| **Backend service** | `backend/services/workflow_builder.py:list_workflow_builder_connectors()` (line 23) |
| **Database tables** | `connectors` |
| **Related metadata** | `integration_presets` (provider catalog defaults) |

**Source of truth**: `connectors` table rows. Any connector option shown in the builder must originate from this persistent location.

Schema ownership note: PostgreSQL schema evolution is migration-driven through Alembic (`alembic.ini`, `backend/migrations/`), with `backend/database.py` as the runtime DB helper layer.

Note: The Settings -> Connectors UI must fetch live connector availability from `GET /api/v1/connectors` (database-backed) on initial page load and must not rely on a cached `settings` payload as the authoritative source for connector availability.

---

#### Builder Metadata

| Component | Path |
|---|---|
| **Frontend consumer** | `ui/src/automation/builder-api.ts:loadBuilderSupportData` |
| **API endpoint** | `GET /api/v1/automations/builder-metadata` |
| **Backend route handler** | `backend/routes/automations.py:get_automation_builder_metadata_endpoint()` |
| **Backend service** | `backend/services/workflow_builder.py:get_automation_builder_metadata()` |
| **Database tables** | **None** (backend-owned constants exposed as scoped metadata) |

**Source of truth**: backend automation-domain option constants for `trigger_types`, `step_types`, `http_methods`, `storage_types`, and `log_column_types`.

The frontend must render these backend-owned builder option sets from metadata and must not recreate them as local runtime literals.

---

#### Connector Activities

| Component | Path |
|---|---|
| **Frontend component** | `ui/src/automation/step-modals/connector-activity-step-form.tsx` |
| **HTML element** | `#add-step-connector-activity-activity-input` (`<select>`) |
| **API endpoint** | `GET /api/v1/connectors/activity-catalog` |
| **Backend route handler** | `backend/routes/connectors.py:list_connector_activity_catalog()` (line 19) |
| **Backend service** | `backend/services/connector_activities_catalog.py:build_connector_activity_catalog()` (line 19) |
| **Database tables** | `connector_endpoint_definitions` |
| **Seed definitions** | `backend/services/connector_activities_google*.py` modules |

**Source of truth**: persisted rows in `connector_endpoint_definitions` with `endpoint_kind = activity`. Code catalogs provide seed/default content only.

Current seeded provider coverage: Google and GitHub. Notion and Trello connectors can be saved in Settings, but they do not yet expose provider-specific builder activities.

---

#### HTTP Presets

| Component | Path |
|---|---|
| **Frontend component** | `ui/src/automation/step-modals/http-step-form.tsx` |
| **HTML element** | `#add-step-http-preset-input` (`<select>`) |
| **API endpoint** | `GET /api/v1/connectors/http-presets` |
| **Backend route handler** | `backend/routes/connectors.py:list_http_presets()` (line 27) |
| **Backend service** | `backend/services/http_presets.py:build_http_preset_catalog()` |
| **Database tables** | `connector_endpoint_definitions` |

**Source of truth**: persisted rows in `connector_endpoint_definitions` with `endpoint_kind = http_preset`. `DEFAULT_HTTP_PRESET_CATALOG` remains seed/default content.

Current seeded provider coverage: Google and GitHub. Notion and Trello automation usage currently falls back to generic HTTP steps rather than provider-specific presets.

---

#### Scripts (Reusable Script Library)

| Component | Path |
|---|---|
| **Frontend component** | `ui/src/automation/step-modals/script-step-form.tsx` |
| **HTML element** | `#add-step-script-input` (`<select>`) |
| **API endpoint** | `GET /api/v1/scripts` |
| **Backend route handler** | `backend/routes/scripts.py:scripts()` (line 20) |
| **Backend service** | Inline SQL in route (no separate service) |
| **Database table** | `scripts` (id, name, description, language, sample_input, validation_status, created_at, updated_at) |

**Source of truth**: `scripts` table. All available reusable scripts for automation steps.

#### Script Language Metadata

| Component | Path |
|---|---|
| **Frontend consumers** | `ui/src/scripts-library/main.ts`, `ui/src/automation/builder-api.ts` |
| **API endpoint** | `GET /api/v1/scripts/metadata` |
| **Backend route handler** | `backend/routes/scripts.py:get_scripts_metadata_endpoint()` |
| **Backend service** | `backend/services/scripts.py:get_scripts_metadata()` |
| **Database tables** | **None** (scripts-domain metadata endpoint) |

**Source of truth**: backend scripts-domain metadata for supported languages. The scripts page and automation script modal should consume the same language list.

---

#### Settings Option Metadata

| Component | Path |
|---|---|
| **Frontend consumer** | `ui/scripts/settings.js` |
| **API endpoint** | `GET /api/v1/settings` |
| **Backend route handler** | `backend/routes/settings.py:get_app_settings()` |
| **Backend service** | `backend/services/automation_execution.py:get_settings_payload()` |
| **Database tables** | `settings` |

**Source of truth**: the `options` block in the settings payload for `notification_channels`, `notification_digests`, and `data_export_windows`.

Frontend fallback state should keep only shape-safe empty values and must not become a second source of truth for these backend-owned choices.

---

#### Connector Settings Metadata

| Component | Path |
|---|---|
| **Frontend consumers** | `ui/scripts/settings/connectors/*.js`, `ui/scripts/apis/forms.js` |
| **API endpoint** | `GET /api/v1/connectors` |
| **Backend route handler** | `backend/routes/connectors.py:list_connectors()` |
| **Backend service** | `backend/services/connectors.py:sanitize_connector_settings_for_response()` |
| **Database tables** | `connectors`, `connector_auth_policies`, `integration_presets` |

**Source of truth**: connector-domain metadata in the connectors response, including normalized provider IDs, `request_auth_type`, connector statuses, auth-policy option lists, and provider preset scope recommendations.

---

#### Dashboard Log Metadata

| Component | Path |
|---|---|
| **Frontend consumer** | `ui/src/dashboard/app.tsx` |
| **API endpoint** | `GET /api/v1/dashboard/logs` |
| **Backend route handler** | `backend/routes/runtime.py:get_dashboard_logs_endpoint()` |
| **Backend service** | `backend/services/automation_execution.py:get_runtime_dashboard_logs_response()` |
| **Database tables** | `settings` plus runtime log files |

**Source of truth**: dashboard/logs metadata in the response payload for allowed log levels. Dashboard time-window filters remain frontend-local and are centralized in `ui/src/dashboard/constants.ts`.

---

#### Tools Manifest

| Component | Path |
|---|---|
| **Frontend component** | `ui/src/automation/tool-step-fields.tsx` |
| **API endpoint** | `GET /api/v1/tools` |
| **Backend route handler** | `backend/routes/tools.py:serve_tools()` (line 58) |
| **Backend service** | `backend/services/tool_runtime.py:build_tool_directory_response()` (line 537) |
| **Database table** | `tools` (id, source_name, source_description, enabled, input/output schemas) |
| **Initialization** | `backend/tool_registry.py:sync_tools_to_database()` (line 291) seeds `DEFAULT_TOOL_CATALOG` at app startup |

**Source of truth**: `tools` table at runtime. Default tools are synced from code at app startup; user-managed tools are persisted in the database.

---

#### Inbound APIs (Dashboard context)

| Component | Path |
|---|---|
| **Frontend component** | Dashboard API registry view |
| **API endpoint** | `GET /api/v1/inbound` |
| **Backend route handler** | `backend/routes/apis.py:inbound_apis()` (line 22) |
| **Backend service** | Inline SQL in route |
| **Database tables** | `inbound_apis` (joined with `inbound_api_events` for event counts) |

**Source of truth**: `inbound_apis` table.

---

### Adding New Data Lineage

When adding a new dropdown or data source to the automation builder or any frontend component:

1. Document the complete path in this section with the template above.
2. Add a traceability comment in the frontend component (see "Code Traceability" below).
3. Add a corresponding backend comment in the route handler and service.
4. Update this section whenever the data source changes.

### Code Traceability

All frontend data fetches should include a comment referencing this section:

```typescript
// Data lineage: See README.md > Data Lineage Reference > Saved Connectors
const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);

useEffect(() => {
  api.get('/api/v1/automations/workflow-connectors')
    .then(data => setConnectors(data));
}, []);
```

Backend route handlers and services should include a similar comment:

```python
# Data lineage: See README.md > Data Lineage Reference > Saved Connectors
@router.get("/workflow-connectors")
def list_workflow_builder_connectors(...):
    # Queries connectors table rows
```

## Troubleshooting

### Port conflicts

Common ports:

- `5432` PostgreSQL
- `8000` FastAPI/Uvicorn
- `4173` Playwright server default (auto-falls forward when busy)
- `2525` SMTP tool listener (tool config dependent)

- `./malcom` requires `8000` to be free and aborts if it is occupied.
- When available, `./malcom` prints existing listeners with `lsof` before exiting.
- Playwright starts at `4173` and automatically selects the next free port if needed.
- When startup or Playwright launch fails, check active listeners first and inspect `backend/data/logs/` for companion startup/runtime errors.

### Playwright/browser setup

Install browsers once:

```bash
cd ui && npm run test:e2e:install
```

Target a specific port when needed:

```bash
cd ui && PLAYWRIGHT_PORT=4190 npx playwright test <spec>
```

## Contributing

1. Read `AGENTS.md` before implementation work.
2. Keep changes small and aligned with existing source-of-truth files.
3. Add or update relevant tests in the same change when behavior changes.
4. Use `./scripts/test-precommit.sh` for normal iteration.
5. Use `bash ./scripts/test-full.sh` for user-visible workflow changes, shared frontend or test-infra changes, and browser workflow validation.
6. Update `ui/e2e/` when user-visible workflows change.
7. Keep `/health` and `/api/v1/**` smoke coverage aligned with `tests/test_api_smoke_matrix.py` and `tests/api_smoke_registry/`.
8. Manually verify the served route when HTML/script wiring changes, in addition to build and test coverage.
9. Do not hand-edit generated outputs such as `ui/dist/**`; regenerate artifacts like the tools manifest from source.
