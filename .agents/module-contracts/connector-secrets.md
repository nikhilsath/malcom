# Module Contract: connector_secrets

**File:** `backend/services/connector_secrets.py`

## Responsibility
Pure-Python XOR-stream encryption with HMAC signature for connector credential fields. No database or framework dependencies.

## Exports

### Constants
- `CONNECTOR_PROTECTION_VERSION` — Token prefix `"enc_v1"`
- `CONNECTOR_NONCE_BYTES` — 16
- `CONNECTOR_SIGNATURE_BYTES` — 32
- `CONNECTOR_SECRET_FIELD_INPUTS` — Mapping from field name to input key

### Functions
- `get_connector_protection_secret(*, root_dir, db_path) -> str` — Derives the workspace protection secret from env or seed
- `derive_connector_protection_key(protection_secret) -> bytes` — SHA-256 key derivation
- `build_connector_keystream(key, nonce, length) -> bytes` — CTR-mode keystream generator
- `protect_connector_secret_value(value, protection_secret) -> str` — Encrypts + signs a plaintext credential
- `unprotect_connector_secret_value(value, protection_secret) -> str | None` — Decrypts and verifies a protected token
- `mask_connector_secret(value) -> str | None` — Returns a masked display string
- `extract_connector_secret_map(auth_config, protection_secret) -> dict[str, str]` — Decrypts all secret fields from an auth_config dict

## Constraints
- No imports from `backend.database`, `backend.services.connectors`, or any other service module
- All functions must be stateless (no module-level mutable state)
- `protect_connector_secret_value` always produces a new random nonce (non-deterministic output)
- `unprotect_connector_secret_value` returns `None` for tampered or malformed tokens (never raises)
