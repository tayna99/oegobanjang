// 공용 데이터 타입 — reference/specs/1단계_화면상태스펙_M1-M9_v1.md §0.4 이식 (M0.3).
// 화면·스토어·mock이 공유하는 계약. 여기 없는 필드는 스펙에 먼저 추가한다.

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type CaseState =
  | 'draft'
  | 'risk_review'
  | 'approval_pending'
  | 'returned' // 반려 — 승인 요청이 사유와 함께 되돌아온 상태 (Mobile.dc.html §2c, 블루프린트 §3)
  | 'human_approved'
  | 'completed'
  | 'blocked';

// 에이전트 파이프라인 단계 — 디자인 §3a/§2a 어휘(블루프린트 §3). CaseState(승인 규율)와
// 별개 축: 에이전트가 케이스를 어디까지 준비했는지를 나타낸다.
export type AgentStage = 'detected' | 'collecting' | 'drafted' | 'awaiting_approval' | 'executed';

export type Role = 'manager' /* 담당자 */ | 'owner' /* 대표 */;

// 'locked'는 저장값이 아니라 근거 게이트 파생 표시(usableCitations 0건) — 서버 값이 아님.
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'locked';

export type NextActionState = 'ready' | 'locked' | 'scheduled' | 'waiting';

// F = 합성 데이터 — 근거로 사용 불가(디자인 §3c 각주, 2026-07-11 비준). C는 정의만 유지.
export type CitationGrade = 'A' | 'B' | 'C' | 'E' | 'F';

// 근거 라이브러리 레코드 상태 — 디자인 §3c 상태 칩(공식 근거/검토 필요/부족 stale/내부 기준).
export type CitationStatus = 'official' | 'review_needed' | 'stale' | 'internal';

export type NextActionKind = 'approve' | 'draft' | 'detail' | 'thread' | 'package' | 'confirm';

export interface NextActionRef {
  actionId: string;
  label: string; // "초안 보기" | "보내기 승인" | "응답 요약 보기" ...
  state: NextActionState;
  requiresApproval: boolean;
  kind: NextActionKind; // 탭 시 이동할 곳(M0.5엔 없었음, 1.3에서 추가 — rules/frontend.md "문자열 라벨로 분기 금지")
}

export interface WorkerRef {
  displayName: string; // 디자인 표기 전체 이름 ("Nguyen Van A") — 블루프린트 §3
  nationality: string;
  team?: string; // "제조1팀" — 디자인 §2a/§3a/§3b 부제의 소속 (블루프린트 §3)
  maskLevel: 'masked';
}

export interface CaseCard {
  caseId: string; // 내부 슬러그(라우팅 키) — 화면 표기는 caseCode를 쓴다
  caseCode: string; // "case_002" — 디자인 §2b/§3b 표기용 케이스 코드
  title: string; // "체류기간 연장 서류 요청" — 업무 단위(근로자명 미포함, 블루프린트 §3)
  workerRef?: WorkerRef;
  severity: Severity;
  dDay?: number; // 음수=경과
  stayExpiryDate?: string; // "2026.08.09" — 디자인 §2b/§3b 메타 라인
  missingDocCount?: number;
  assignee?: string; // "김담당"/"박주임" — 디자인 §3a 담당 컬럼
  evidenceCompleteness?: number; // 0~100 — 디자인 §3a 근거 완성도
  agentStage?: AgentStage; // 파이프라인 단계 — 없으면 상태에서 파생(caseStage.ts)
  state: CaseState;
  approvalRequired: boolean;
  primaryAction: NextActionRef;
  secondaryAction: NextActionRef;
  preparedBy: 'agent' | 'rule'; // 프로액티브 런이 준비한 카드는 'agent'
  preparedRunRef?: string; // "AI가 준비를 마쳤습니다 · 런 #4791 보기" 링크
}

export interface Citation {
  id?: string; // "cit_001" — 근거 라이브러리 레코드 참조(블루프린트 §3)
  grade: CitationGrade;
  title: string;
  source: string;
  updatedAt: string;
}

// 근거 라이브러리 레코드 — 디자인 §3c. 케이스 시트의 Citation은 이 레코드의 부분집합이다.
export interface CitationRecord extends Citation {
  id: string;
  status: CitationStatus;
}

// --- 스토어 계약 (M0.4) ---

export interface Approval {
  actionId: string;
  status: ApprovalStatus;
  // pending 요청에는 결정 키가 아직 없고, decide()에서만 non-empty 키를 기록한다.
  idempotencyKey: string | null; // 중복 승인 차단 키 (GOTCHAS §2)
  reason?: string; // 반려 사유 — "반려 시 사유가 판단 기록에 남고 요청이 되돌아갑니다" (Mobile §2c)
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
  | 'review_started' // 사례 검토 진입 (Mobile §2d 타임라인, 블루프린트 §3)
  | 'checklist_completed' // 승인 체크리스트 완료 (Mobile §2d)
  | 'exported' // 패키지 내보내기 (PC §3c 감사 로그 '내보내기' — export_00NN)
  | 'final_response_generated'
  | 'interpretation_confirmed';

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

export type Channel = 'sms' | 'alimtalk' | 'zalo' | 'email';
export type MessageDirection = 'out' | 'in';
export type MessageDeliveryStatus = 'draft' | 'pending_approval' | 'sent';
export interface Message {
  messageId: string; threadId: string; direction: MessageDirection; channel: Channel;
  body: string; lang: string; at: string; deliveryStatus?: MessageDeliveryStatus;
  evidenceRef?: string; caseId?: string; externalId?: string;
}
export interface InterpretationUpdate { updateId: string; field: string; from: string; to: string; badgeTone: string; }
export interface Interpretation {
  interpretationId: string; threadId: string; caseId: string; summaryKo: string;
  confidence: 'high' | 'low'; updates: InterpretationUpdate[];
  recommendedActions: { action: NextActionRef; reason: string }[]; isFinal: false;
  confirmedSummary?: string; confirmedCardText?: string; evidenceRef?: string;
}
export interface MessageThread {
  threadId: string; workerRef: WorkerRef; channel: Channel; channelLabel: string;
  caseId?: string; draftCaseId?: string; messages: Message[]; interpretation?: Interpretation;
  interpretationStatus: 'none' | 'pending_review' | 'confirmed'; preview: string;
  timeLabel: string; reminderScheduledLabel?: string;
}
