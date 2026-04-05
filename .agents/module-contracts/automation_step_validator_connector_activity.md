Owner: backend/services/automation_step_validators
Responsibilities:
- Validate `connector_activity` step configuration: connector existence, activity availability, scopes, and input schema validity.

Public API:
- `validate_connector_activity_step(step, index, connection) -> list[str]`

Owned DB tables:
- reads `connectors` table for validation; does not own tables.

Inbound dependencies:
- `backend/services/connector_activities`
- `backend/services/connectors`

Allowed callers:
- `backend/services/validation.py`

Test obligations:
- Unit tests for missing connector, unsupported activity, missing scopes, and invalid inputs.

Example callsite:
```
issues.extend(validate_connector_activity_step(step, index, connection))
```
