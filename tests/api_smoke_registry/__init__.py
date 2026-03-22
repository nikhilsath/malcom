from __future__ import annotations

from .automation_log_cases import AUTOMATION_LOG_CASES
from .core import (
    RouteSmokeCase,
    all_discovered_route_signatures,
    case_signature,
    create_smoke_context,
    get_internal_api_route_signatures,
    invoke_smoke_case,
)
from .inbound_outgoing_cases import INBOUND_OUTGOING_CASES
from .runtime_workers_cases import RUNTIME_WORKERS_CASES
from .scripts_cases import SCRIPTS_CASES
from .settings_connectors_cases import SETTINGS_CONNECTORS_CASES
from .tools_cases import TOOLS_CASES

SMOKE_CASE_GROUPS: dict[str, tuple[RouteSmokeCase, ...]] = {
    "runtime/workers": RUNTIME_WORKERS_CASES,
    "scripts": SCRIPTS_CASES,
    "settings/connectors": SETTINGS_CONNECTORS_CASES,
    "tools": TOOLS_CASES,
    "inbound/outgoing APIs": INBOUND_OUTGOING_CASES,
    "automations/log tables/runs": AUTOMATION_LOG_CASES,
}

SMOKE_CASES: tuple[RouteSmokeCase, ...] = tuple(
    case for group_cases in SMOKE_CASE_GROUPS.values() for case in group_cases
)

ROUTE_SCENARIO_MAP: dict[str, str] = {
    case_signature(case): case.name
    for case in SMOKE_CASES
}


def validate_route_scenario_mapping() -> tuple[list[str], list[str]]:
    discovered = all_discovered_route_signatures()
    mapped = set(ROUTE_SCENARIO_MAP)
    missing = sorted(discovered - mapped)
    extra = sorted(mapped - discovered)
    print(f"Discovered routes missing smoke scenarios: {missing}")
    print(f"Smoke scenario mappings for removed routes: {extra}")
    return missing, extra
