"""P1 코어 18테이블 모델 — docs/DB_SCHEMA.md §10. 전부 여기서 임포트해 Base.metadata를 완성한다.

P2(소통·패키지)·P3(계정 심화·알림·에이전틱) 테이블은 해당 마일스톤 착수 시 이 패키지에 추가한다.
"""

from app.models.approval import Approval
from app.models.briefing import Briefing, BriefingItem
from app.models.case import Case, NextAction
from app.models.citation import CaseCitation, Citation
from app.models.company import Company
from app.models.document import DocumentRequirement, WorkerDocument
from app.models.draft import Draft, DraftVariant
from app.models.evidence import EvidenceEvent
from app.models.membership import Membership
from app.models.run import Run, RunStep
from app.models.user import User
from app.models.worker import Worker

__all__ = [
    "Approval",
    "Briefing",
    "BriefingItem",
    "Case",
    "NextAction",
    "CaseCitation",
    "Citation",
    "Company",
    "DocumentRequirement",
    "WorkerDocument",
    "Draft",
    "DraftVariant",
    "EvidenceEvent",
    "Membership",
    "Run",
    "RunStep",
    "User",
    "Worker",
]
