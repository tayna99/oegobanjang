from __future__ import annotations

from threading import RLock

from .schemas import LangChainRuntimeState


class LangChainRuntimeStateStore:
    """Process-local runtime state store.

    This replaces the custom graph MemorySaver for P0. DB snapshot persistence
    is handled separately; approval review sync is status-only and must never
    resume an agent or execute external delivery.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._states: dict[str, LangChainRuntimeState] = {}

    def save(self, state: LangChainRuntimeState) -> None:
        with self._lock:
            self._states[state.request_id] = state

    def get(self, request_id: str) -> LangChainRuntimeState | None:
        with self._lock:
            return self._states.get(request_id)

    def mark_approval_reviewed(
        self,
        request_id: str,
        *,
        status: str,
        reason: str | None = None,
    ) -> bool:
        """Update hot runtime state after the shared approval API reviews it.

        This does not resume an agent run or execute any external action. It only
        prevents `/agent/state/{request_id}` from returning stale PENDING data
        while the process-local store is still warm.
        """

        with self._lock:
            state = self._states.get(request_id)
            if state is None:
                return False
            state.approval.required = True
            state.approval.status = status  # type: ignore[assignment]
            state.structured_response.approval.required = True
            state.structured_response.approval.status = status  # type: ignore[assignment]
            if reason:
                state.approval.reason = reason
                state.structured_response.approval.reason = reason
            return True

    def clear(self) -> None:
        with self._lock:
            self._states.clear()


runtime_state_store = LangChainRuntimeStateStore()
