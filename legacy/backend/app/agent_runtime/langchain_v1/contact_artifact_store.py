from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any


_LOCK = RLock()
_STORE: dict[str, dict[str, Any]] = {}


def save_contact_artifacts(request_id: str, artifacts: dict[str, Any]) -> None:
    if not request_id or not artifacts:
        return
    with _LOCK:
        _STORE[request_id] = deepcopy(artifacts)


def get_contact_artifacts(request_id: str) -> dict[str, Any]:
    if not request_id:
        return {}
    with _LOCK:
        return deepcopy(_STORE.get(request_id) or {})


def pop_contact_artifacts(request_id: str) -> dict[str, Any]:
    if not request_id:
        return {}
    with _LOCK:
        return deepcopy(_STORE.pop(request_id, {}))
