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

export type NextActionKind = 'approve' | 'draft' | 'detail' | 'thread' | 'package' | 'confirm';

export interface NextActionRef {
  actionId: string;
  label: string; // "초안 보기" | "보내기 승인" | "응답 요약 보기" ...
  state: NextActionState;
  requiresApproval: boolean;
  kind: NextActionKind; // 탭 시 이동할 곳(M0.5엔 없었음, 1.3에서 추가 — rules/frontend.md "문자열 라벨로 분기 금지")
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
  | 'final_response_generated'
  | 'interpretation_confirmed'; // M6 응답 해석 확인 (docs/MESSAGING_CHANNELS.md §4)

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

// --- 메시징 도메인 (M6 응답 해석) — docs/MESSAGING_CHANNELS.md §4가 스펙 원본.
// 필드를 바꿀 일이 있으면 그 문서부터 고친다(문서와 코드가 어긋나면 안 된다).

export type Channel = 'sms' | 'alimtalk' | 'zalo' | 'email'; // 근로자 채널 3종(sms/alimtalk/zalo) + 행정사 패키지 전용(email)

export type MessageDirection = 'out' /* 담당자→근로자 */ | 'in' /* 근로자→담당자, 인바운드 정규화 결과 */;

// 백엔드 확장 예약: 'queued' | 'delivered' | 'failed' (Outbox가 실제 큐가 되는 시점부터 추가)
export type MessageDeliveryStatus = 'draft' | 'pending_approval' | 'sent';

export interface Message {
  messageId: string;
  threadId: string;
  direction: MessageDirection;
  channel: Channel;
  body: string; // 스레드 내부 렌더 전용 — 목록 미리보기/evidence 요약 노출 금지 (GOTCHAS §3)
  lang: string; // 근로자 모국어 코드 ('vi' | 'mn' | 'bn' ...) — 'ko'는 담당자 발신
  at: string; // ISO timestamp
  deliveryStatus?: MessageDeliveryStatus; // direction:'in'이면 없음
  evidenceRef?: string; // "#4789" — approval_decided 등 관련 판단 기록
  caseId?: string; // 스레드는 케이스와 1:1이 아니므로 메시지 단위로도 보관
  externalId?: string; // 어댑터가 반환한 채널사 메시지 ID. MockAdapter는 항상 undefined
}

// Interpretation.updates 원소 — 서류 상태 등 필드 단위 갱신 제안 1건
export interface InterpretationUpdate {
  field: string; // 갱신 대상 필드명("표준근로계약서" 등)
  from: string; // 갱신 전 상태 라벨
  to: string; // 갱신 후 상태 라벨
  badgeTone: string; // src/lib/badgeTone.ts BadgeTone 값 — Interpretation은 badgeTone 구현을 몰라야 하므로 string으로 느슨하게 연결
}

export interface Interpretation {
  interpretationId: string;
  threadId: string;
  caseId: string;
  summaryKo: string; // 근로자 응답의 한국어 요약 — 원문 문장을 포함하지 않는다
  confidence: 'high' | 'low'; // low면 "해석이 불확실합니다. 원문을 확인해주세요" 안내 필요 (1단계 M6)
  updates: InterpretationUpdate[];
  recommendedActions: { action: NextActionRef; reason: string }[]; // 기존 NextActionRef 재사용 — 문자열 라벨로 분기 금지(rules/frontend.md)
  isFinal: false; // 담당자 확인 전 확정 금지 (GLOSSARY.md: Interpretation "isFinal:false 필수")
  confirmedSummary?: string; // onConfirm 이후 확정된 요약. Evidence summary와 동일 문장이어야 함
  confirmedCardText?: string; // 확정 후 케이스 카드/브리핑에 노출할 축약 문구
  evidenceRef?: string;
}

export interface MessageThread {
  threadId: string;
  workerRef: WorkerRef; // 마스킹 원칙 동일 적용
  channel: Channel;
  channelLabel: string; // "Zalo" | "SMS" 등 표시용. 국적과 마찬가지로 색상 강조 금지
  caseId?: string; // 현재 연결된 케이스
  draftCaseId?: string; // 케이스 생성 전 임시 연결
  messages: Message[];
  interpretation?: Interpretation;
  interpretationStatus: 'none' | 'pending_review' | 'confirmed';
  preview: string; // 목록 미리보기 — 원문 대신 상태 요약만 (GOTCHAS §3)
  timeLabel: string;
  reminderScheduledLabel?: string; // "리마인드 7.6 예정" 형식
}
