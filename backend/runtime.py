from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class RuntimeTrigger:
    type: str
    api_id: str
    event_id: str
    payload: Any
    received_at: str


class RuntimeEventBus:
    def __init__(self) -> None:
        self._lock = Lock()
        self._history: list[RuntimeTrigger] = []

    def emit(self, trigger: RuntimeTrigger) -> None:
        with self._lock:
            self._history.append(trigger)

    def history(self) -> list[RuntimeTrigger]:
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


runtime_event_bus = RuntimeEventBus()
