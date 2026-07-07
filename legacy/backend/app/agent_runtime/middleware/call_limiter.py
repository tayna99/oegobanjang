"""Call limiter: 세션당 LLM/tool 호출 횟수를 제한합니다."""
from dataclasses import dataclass, field
from app.agent_runtime.schemas import ForeignHiringState

MAX_LLM_CALLS = 10
MAX_TOOL_CALLS = 20


@dataclass
class CallCounter:
    llm_calls: int = 0
    tool_calls: int = 0
    _counters: dict[str, int] = field(default_factory=dict)

    def increment_llm(self) -> bool:
        self.llm_calls += 1
        return self.llm_calls <= MAX_LLM_CALLS

    def increment_tool(self, tool_name: str) -> bool:
        self.tool_calls += 1
        self._counters[tool_name] = self._counters.get(tool_name, 0) + 1
        return self.tool_calls <= MAX_TOOL_CALLS

    @property
    def llm_limit_reached(self) -> bool:
        return self.llm_calls >= MAX_LLM_CALLS

    @property
    def tool_limit_reached(self) -> bool:
        return self.tool_calls >= MAX_TOOL_CALLS


_session_counters: dict[str, CallCounter] = {}


def get_counter(request_id: str) -> CallCounter:
    if request_id not in _session_counters:
        _session_counters[request_id] = CallCounter()
    return _session_counters[request_id]


def check_llm_limit(state: ForeignHiringState) -> tuple[bool, str]:
    counter = get_counter(state.request_id)
    allowed = counter.increment_llm()
    if not allowed:
        return False, f"LLM 호출 한도 초과 ({MAX_LLM_CALLS}회). 요청을 분리해서 진행해주세요."
    return True, ""


def check_tool_limit(state: ForeignHiringState, tool_name: str) -> tuple[bool, str]:
    counter = get_counter(state.request_id)
    allowed = counter.increment_tool(tool_name)
    if not allowed:
        return False, f"Tool 호출 한도 초과 ({MAX_TOOL_CALLS}회)."
    return True, ""
