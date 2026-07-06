// 공용 데이터 타입 — reference/specs/1단계_화면상태스펙_M1-M9_v1.md §0.4 이식 (M0.3).
// 화면·스토어·mock이 공유하는 계약. 여기 없는 필드는 스펙에 먼저 추가한다.

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type CaseState =
  | 'draft'
  | 'risk_review'
  | 'approval_pending'
  | 'human_approved'
  | 'completed'
  | 'blocked';

export type Role = 'manager' /* 담당자 */ | 'owner' /* 대표 */;

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'locked';

export type NextActionState = 'ready' | 'locked' | 'scheduled' | 'waiting';

export type CitationGrade = 'A' | 'B' | 'C' | 'E';

export interface NextActionRef {
  actionId: string;
  label: string; // "초안 보기" | "보내기 승인" | "응답 요약 보기" ...
  state: NextActionState;
  requiresApproval: boolean;
}

export interface WorkerRef {
  displayName: string;
  nationality: string;
  maskLevel: 'masked';
}

export interface CaseCard {
  caseId: string;
  title: string; // "Nguyen V. 체류기간 연장 서류 요청" (업무 단위)
  workerRef?: WorkerRef;
  severity: Severity;
  dDay?: number; // 음수=경과
  missingDocCount?: number;
  state: CaseState;
  approvalRequired: boolean;
  primaryAction: NextActionRef; // CTA 2개 고정 원칙
  secondaryAction: NextActionRef;
  preparedBy: 'agent' | 'rule'; // 프로액티브 런이 준비한 카드는 'agent'
  preparedRunRef?: string; // "AI가 준비를 마쳤습니다 · 런 #4791 보기" 링크
}

export interface Citation {
  grade: CitationGrade;
  title: string;
  source: string;
  updatedAt: string;
}

// --- 스토어 계약 (M0.4) ---

export interface Approval {
  actionId: string;
  status: ApprovalStatus;
  idempotencyKey: string; // 중복 승인 차단 키 (GOTCHAS §2)
}

// Evidence Log 이벤트 타입 (AGENTS.md §9). 원문·PII 필드는 두지 않는다 — 해시만.
export type EvidenceType =
  | 'intent_classified'
  | 'plan_created'
  | 'tool_executed'
  | 'rag_retrieved'
  | 'risk_flagged'
  | 'approval_requested'
  | 'approval_decided'
  | 'final_response_generated';

export interface EvidenceEvent {
  id: string;
  type: EvidenceType;
  at: string; // ISO timestamp (주입 가능)
  caseId?: string;
  actionId?: string;
  hash?: string; // 민감정보는 원문 대신 해시만
  // --- 표시용 필드 (M0.5, 1단계 스펙 M8 EventTimelineItem 이식) ---
  summary?: string; // PII 마스킹된 한 줄 요약만. 원문 메시지 전문 금지
  actor?: string; // "시스템" | "김담당 (본인 확인 완료)" — 원문 개인정보 아님
  evidenceRef?: string; // "#4789" 표시용 판단 기록 번호 (id와 별개 — id는 내부 식별자)
}
