Owner: backend/services/automation_step_executors
Responsibilities:
- Execute `llm_chat` automation steps, delegate to the LLM/chat service, and normalize runtime results.

Public API:
- `execute_llm_chat_step(connection, logger, *, step, context) -> dict` — returns runtime result dict or raises on fatal errors.

Owned DB tables:
- None (reads settings/config as needed).

Inbound dependencies:
- `backend/services/llm_chat_service` (canonical LLM interface)

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests must validate delegation to `llm_chat_service` and result normalization for success and error flows.
