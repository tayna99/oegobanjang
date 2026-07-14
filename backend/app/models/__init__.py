"""ORM 쿼리 전용 모델 — db/schema.sql의 31개 테이블 전부를 매핑한다.

실제 스키마(테이블·FK·CHECK·트리거·뷰)는 db/schema.sql을 그대로 실행하는 마이그레이션이 만든다.
이 패키지의 모델은 테이블명 + 컬럼만 매핑해 서비스 계층이 조회·삽입할 수 있게 한다.
FK·CHECK·복합 UNIQUE·Index·relationship은 선언하지 않는다(DB가 소유).
"""

from app.models.agent_note import AgentNote
from app.models.approval import Approval
from app.models.autonomy import AutonomyGrant
from app.models.briefing import Briefing, BriefingItem
from app.models.case import Case, NextAction
from app.models.citation import CaseCitation, Citation
from app.models.company import Company
from app.models.csv_import import CsvImport
from app.models.delegation import Delegation
from app.models.document import DocumentRequirement, WorkerDocument, WorkerIntakeFile
from app.models.draft import Draft, DraftVariant
from app.models.evidence import EvidenceEvent
from app.models.handoff import HandoffPackage, PackageExport
from app.models.interpretation import Interpretation, StatusUpdateProposal
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.run import Run, RunStep
from app.models.stat_snapshot import StatSnapshot
from app.models.thread import Thread, ThreadMessage
from app.models.user import User
from app.models.worker import Worker

__all__ = [
    "AgentNote",
    "Approval",
    "AutonomyGrant",
    "Briefing",
    "BriefingItem",
    "Case",
    "NextAction",
    "CaseCitation",
    "Citation",
    "Company",
    "CsvImport",
    "Delegation",
    "DocumentRequirement",
    "WorkerDocument",
    "WorkerIntakeFile",
    "Draft",
    "DraftVariant",
    "EvidenceEvent",
    "HandoffPackage",
    "PackageExport",
    "Interpretation",
    "StatusUpdateProposal",
    "Membership",
    "Notification",
    "Run",
    "RunStep",
    "StatSnapshot",
    "Thread",
    "ThreadMessage",
    "User",
    "Worker",
]
