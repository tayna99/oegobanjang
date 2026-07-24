import { calcDday } from '@/lib/dday';
import { useSessionStore } from '@/stores/sessionStore';
// 타입 전용 import(런타임에 지워짐) — SD-6이 CaseDetail의 새 필드를 mock CaseSheet와
// 같은 모양으로 맞춰(checkedItems/docs) 화면이 mock/real을 공유 로직으로 다루게 한다.
import type { CaseCheckedItem, CaseDoc, CaseDocStatus } from '@/mocks/fixtures';
import type { AgentStage, CaseCard, NextActionRef, WorkerRef } from '@/types';
import { apiFetch } from './client';

// GET /api/v1/cases 응답 DTO(백엔드 backend/app/schemas/case.py의 CaseOut 그대로, snake_case) —
// R2.3, NEXT_ROADMAP 2.3. briefings.ts가 이 타입·toCaseCard()를 그대로 재사용한다.
export interface WorkerRefDto {
  display_name: string;
  nationality: string;
  team: string | null;
}

export interface NextActionDto {
  action_id: string;
  label: string;
  state: string;
  requires_approval: boolean;
  kind: string;
}

export interface CaseDto {
  id: string;
  case_code: string;
  title: string;
  severity: string;
  state: string;
  agent_stage: string | null;
  due_date: string | null;
  approval_required: boolean;
  prepared_by: string;
  prepared_run_id: string | null;
  worker: WorkerRefDto | null;
  primary_action: NextActionDto | null;
  secondary_action: NextActionDto | null;
}

function toWorkerRef(dto: WorkerRefDto | null): WorkerRef | undefined {
  if (!dto) return undefined;
  return { displayName: dto.display_name, nationality: dto.nationality, team: dto.team ?? undefined, maskLevel: 'masked' };
}

// next_actions가 아직 없는 케이스(감지만 되고 액션 초안이 안 만들어진 경우)를 위한 안전한
// 기본값 — CaseCard.primaryAction/secondaryAction은 필수 필드라 null을 그대로 못 둔다.
// CSV/온보딩 유입 케이스의 기본 액션(lib/csvUpload.workerToCard)과 같은 패턴.
function toNextAction(
  dto: NextActionDto | null,
  fallback: { actionId: string; label: string; kind: NextActionRef['kind'] },
): NextActionRef {
  if (!dto) {
    return { actionId: fallback.actionId, label: fallback.label, state: 'ready', requiresApproval: false, kind: fallback.kind };
  }
  return {
    actionId: dto.action_id,
    label: dto.label,
    state: dto.state as NextActionRef['state'],
    requiresApproval: dto.requires_approval,
    kind: dto.kind as NextActionRef['kind'],
  };
}

// R2.3 배선 — 아직 GET /api/v1/cases 응답에 없는 CaseCard 필드(의도적 스코프 축소, 후속 확장
// 대상): stayExpiryDate(WorkerRefOut에 stay_expires_at 미포함) · missingDocCount · assignee ·
// evidenceCompleteness(next_actions/cases에 해당 개념 없음) · preparedRunRef(prepared_run_id는
// 있으나 evidenceRef "#4788" 표기로 변환할 근거[runs.anchor_event_no]가 아직 안 내려온다).
// 여기서 값을 지어내지 않고 undefined로 남긴다 — 화면은 이미 이 필드들을 옵셔널로 다룬다.
export function toCaseCard(dto: CaseDto): CaseCard {
  return {
    caseId: dto.id,
    caseCode: dto.case_code,
    title: dto.title,
    workerRef: toWorkerRef(dto.worker),
    severity: dto.severity as CaseCard['severity'],
    // 실 API 모드는 데모 고정일(DEMO_TODAY)이 아니라 진짜 오늘을 기준으로 dDay를 계산한다 —
    // 실서버 데이터는 데모 세계관 날짜에 묶이지 않는다(lib/dday.ts의 "기준일 주입" 원칙은
    // 테스트 결정성을 위한 것이지, 여기서 new Date()를 쓰는 것과 상충하지 않는다).
    dDay: dto.due_date ? calcDday(dto.due_date, new Date()) : undefined,
    state: dto.state as CaseCard['state'],
    agentStage: (dto.agent_stage as AgentStage | null) ?? undefined,
    approvalRequired: dto.approval_required,
    primaryAction: toNextAction(dto.primary_action, { actionId: `${dto.id}-detail`, label: '상세 보기', kind: 'detail' }),
    secondaryAction: toNextAction(dto.secondary_action, { actionId: `${dto.id}-confirm`, label: '케이스 확인 완료', kind: 'confirm' }),
    preparedBy: dto.prepared_by as CaseCard['preparedBy'],
  };
}

export async function fetchCases(): Promise<CaseCard[]> {
  const token = useSessionStore.getState().token ?? undefined;
  const dtos = await apiFetch<CaseDto[]>('/api/v1/cases', { token });
  return dtos.map(toCaseCard);
}

// GET /api/v1/cases/{case_id} 응답 DTO(R2.4) — CaseOut 필드 전부 + ApprovePage 전용 필드.
export interface PendingApprovalChecklistItemDto {
  key: string;
  label: string;
  checked: boolean;
}

export interface PendingApprovalDto {
  id: string;
  action_id: string;
  checklist: PendingApprovalChecklistItemDto[] | null;
  requested_at: string;
}

// SD-6 — backend/app/schemas/case.py CheckedItemOut/WorkerDocumentOut 그대로.
export interface CheckedItemDto {
  label: string;
  value: string;
}

export interface WorkerDocumentDto {
  doc_type: string;
  status: string;
  due_date: string | null;
  expires_at: string | null;
}

export interface CaseDetailDto extends CaseDto {
  usable_citation_count: number;
  guard_note: string | null;
  pending_approval: PendingApprovalDto | null;
  checked_items: CheckedItemDto[];
  next_wake: string | null;
  documents: WorkerDocumentDto[];
}

export interface PendingApprovalChecklistItem {
  key: string;
  label: string;
  checked: boolean;
}

export interface PendingApproval {
  id: string;
  actionId: string;
  checklist: PendingApprovalChecklistItem[] | null;
  requestedAt: string;
}

// ApprovePage/CaseReviewPage/CaseWorkbench 등이 real 모드에서 CASE_SHEETS(mock) 대신 쓰는
// 필드만 뽑는다 — 카드 본체는 caseStore(fetchCases가 이미 채움)를 그대로 쓴다(중복 조립 방지).
// checkedItems/docs/nextWake는 SD-6(plans/SEED_DESIGN_2026-07-20.md Part B5(c)) — 필드명은
// mock CaseSheet(mocks/fixtures.ts)과 일부러 맞췄다(화면이 동일 렌더 로직을 재사용할 수 있게).
export interface CaseDetail {
  usableCitationCount: number;
  guardNote: string | null;
  pendingApproval: PendingApproval | null;
  checkedItems: CaseCheckedItem[];
  nextWake?: string;
  docs: CaseDoc[];
}

function toPendingApproval(dto: PendingApprovalDto | null): PendingApproval | null {
  if (!dto) return null;
  return {
    id: dto.id,
    actionId: dto.action_id,
    checklist: dto.checklist?.map((item) => ({ key: item.key, label: item.label, checked: item.checked })) ?? null,
    requestedAt: dto.requested_at,
  };
}

// mock CaseDoc.statusLabel은 디자인 원문이 케이스마다 다르게 써 둔 자유 문구("05/12 확인" 등,
// GOTCHAS §3 배지-라벨 병기 관례)라 서버가 그대로 재현할 근거가 없다 — real 모드는 상태값
// 자체를 사람이 읽는 짧은 라벨로만 표시한다(정직한 단순화, CaseDocStatus 6종 전부 커버).
const DOC_STATUS_LABEL: Record<CaseDocStatus, string> = {
  missing: '누락',
  requested: '요청됨',
  received: '확보',
  expiring: '만료 임박',
  company_check: '사내 확인 중',
  pending: '대기',
};

function toCaseDoc(dto: WorkerDocumentDto): CaseDoc {
  const status = dto.status as CaseDocStatus;
  return { name: dto.doc_type, status, statusLabel: DOC_STATUS_LABEL[status] ?? dto.status };
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetail> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<CaseDetailDto>(`/api/v1/cases/${caseId}`, { token });
  return {
    usableCitationCount: dto.usable_citation_count,
    guardNote: dto.guard_note,
    pendingApproval: toPendingApproval(dto.pending_approval),
    checkedItems: dto.checked_items.map((item) => ({ label: item.label, value: item.value })),
    nextWake: dto.next_wake ?? undefined,
    docs: dto.documents.map(toCaseDoc),
  };
}
