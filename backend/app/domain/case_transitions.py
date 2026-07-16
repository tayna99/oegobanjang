"""케이스 상태 전이 화이트리스트 — src/stores/caseStore.ts의 CASE_TRANSITIONS와 정확히 동일한
표(docs/DB_SCHEMA.md §5.1). 서버가 정본이 되어도 이 표는 프론트와 글자 단위로 일치해야 한다.

이 표 밖의 전이는 버그다. returned(반려)는 approval_pending에서만 진입하고, 보완 후 다시
approval_pending으로만 나간다(Mobile §2c, 블루프린트 §3).
"""

CASE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("risk_review",),
    "risk_review": ("approval_pending", "blocked"),
    "approval_pending": ("human_approved", "returned", "blocked"),
    "returned": ("approval_pending",),
    "human_approved": ("completed", "blocked"),
    "completed": (),
    "blocked": (),
}


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in CASE_TRANSITIONS.get(from_state, ())
