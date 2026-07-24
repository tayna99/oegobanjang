import type { ChipTone } from '@/lib/chipTone';
import type { EvidenceEvent, EvidenceType } from '@/types';
import { API_MODE } from '@/lib/api/config';
import { EVIDENCE_SEED } from '@/mocks/evidence';
import type { CaseActivityEntry } from '@/mocks/fixtures';
import { RUN_CONFIGS } from '@/mocks/runs';

// 감사 로그 셰이핑 — PC §3c 거버넌스(2.5.5) + 향후 M8 전역 판단 기록(2.3) 공용.
// reference/design-system/외고반장 PC.dc.html §3c(586~599행): 필터 칩 + ref·타입 칩·시각·행위자·해시.

// EvidenceType → 감사 로그 표시 라벨/톤. 라이프사이클(2d)과 달리 전 타입을 다룬다.
export const AUDIT_TYPE_LABEL: Record<EvidenceType, string> = {
  intent_classified: '의도 분류',
  plan_created: '계획 생성',
  tool_executed: '도구 실행',
  rag_retrieved: '근거 조회',
  risk_flagged: '위험 탐지',
  approval_requested: '승인 요청',
  approval_decided: '승인 완료',
  approval_rejected: '반려',
  review_started: '검토 시작',
  checklist_completed: '체크리스트 완료',
  exported: '내보내기',
  final_response_generated: '응답 생성',
  interpretation_confirmed: '해석 확인', // M6 응답 해석 확인(2.2, threadStore.confirmInterpretation)
  // 7단계 §5 권한 이벤트(운영급 RBAC 확장).
  role_granted: '역할 부여',
  role_changed: '역할 변경',
  member_invited: '구성원 초대',
  member_removed: '구성원 제거',
  delegation_granted: '위임 설정',
  delegation_revoked: '위임 해제',
  approval_escalated: '승인 지연',
  package_link_issued: '패키지 링크 발급',
  package_link_viewed: '패키지 링크 열람',
  dispatch_executed: '발송 실행',
  delivery_confirmed: '전달 확인',
  package_reply: '행정사 회신',
  worker_reply_received: '근로자 응답 수신', // N02 — 응답 링크·Zalo webhook 인바운드(R3 stage ②·④)
};

export const AUDIT_TYPE_TONE: Record<EvidenceType, ChipTone> = {
  intent_classified: 'neutral',
  plan_created: 'neutral',
  tool_executed: 'neutral',
  rag_retrieved: 'approval',
  risk_flagged: 'high',
  approval_requested: 'approval',
  approval_decided: 'positive',
  approval_rejected: 'high',
  review_started: 'neutral',
  checklist_completed: 'draft',
  exported: 'neutral',
  final_response_generated: 'neutral',
  interpretation_confirmed: 'positive',
  // 역할 배지와 달리 이건 상태 톤이 필요한 감사 로그 칩 — 관리 이벤트는 neutral,
  // 에스컬레이션만 위험 계열(high, risk_flagged/approval_rejected와 동일 취급).
  role_granted: 'neutral',
  role_changed: 'neutral',
  member_invited: 'neutral',
  member_removed: 'neutral',
  delegation_granted: 'neutral',
  delegation_revoked: 'neutral',
  approval_escalated: 'high',
  package_link_issued: 'neutral',
  package_link_viewed: 'neutral',
  dispatch_executed: 'neutral',
  delivery_confirmed: 'positive',
  package_reply: 'approval',
  worker_reply_received: 'approval', // 응답 도착 — 검토 유도(interpretation_confirmed 이전 단계)
};

export type AuditFilterKey = 'all' | 'risk' | 'approval' | 'export';

export interface AuditFilter {
  key: AuditFilterKey;
  label: string;
  match: (type: EvidenceType) => boolean;
}

// 디자인 §3c 필터 칩: 전체 / 위험 탐지 / 승인 / 내보내기.
export const AUDIT_FILTERS: AuditFilter[] = [
  { key: 'all', label: '전체', match: () => true },
  { key: 'risk', label: '위험 탐지', match: (t) => t === 'risk_flagged' },
  {
    key: 'approval',
    label: '승인',
    match: (t) =>
      t === 'approval_requested' ||
      t === 'approval_decided' ||
      t === 'approval_rejected' ||
      t === 'approval_escalated', // 7단계 §3.2 에스컬레이션도 승인 흐름의 일부로 취급
  },
  { key: 'export', label: '내보내기', match: (t) => t === 'exported' },
];

// 시드(앱 열기 전 기록)와 런타임 이벤트를 합치되 정렬은 하지 않는다 — 병합 자체는 항상
// "시드 다음 런타임, 각자 자기 순서 유지"로 결정적이다. mergedAuditLog(최신순)와
// mergedAuditLogAscending(오래된 순)이 이 위에서 서로 다른 정렬을 얹는다.
// real 모드는 EVIDENCE_SEED(데모 6인 로스터 픽스처)를 섞지 않는다 — fetchCases()가 mock
// CASE_CARDS를 완전히 대체하는 것과 동일 원칙(R2.3). real 모드의 "시드"는 서버가 이미 가진
// 기록이고, 그건 useSeedEvidence가 evidenceStore에 직접 hydrate하므로 여기 events에 이미 있다.
function mergeSeedAndRuntime(events: readonly EvidenceEvent[]): EvidenceEvent[] {
  if (API_MODE === 'real') return [...events];
  const runtimeIds = new Set(events.map((event) => event.id));
  return [...EVIDENCE_SEED.filter((event) => !runtimeIds.has(event.id)), ...events];
}

// 시드(앱 열기 전 기록) + 런타임 이벤트를 병합해 최신순 정렬. id 중복은 런타임 우선.
// 스토어 자체는 비어 시작하므로(evidenceStore) 시드는 표시 시점에 합친다(블루프린트 §9-A, M8도 동일).
export function mergedAuditLog(events: readonly EvidenceEvent[]): EvidenceEvent[] {
  return mergeSeedAndRuntime(events)
    .slice()
    .sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
}

// CaseHistoryPage 전용 — 생애주기 타임라인은 오래된 것부터 그려야 한다. mergedAuditLog를
// 뒤집어 쓰지 않는다: Array#sort는 안정 정렬이라 동일 시각 이벤트의 상대 순서(시드 다음
// 런타임, 각자 발생/append 순)를 보존하는데, 내림차순 결과를 통째로 reverse()하면 그 tie
// 블록 내부 순서까지 뒤집혀 "체크리스트 완료"·"최종 승인"처럼 같은 밀리초에 연달아 append된
// 이벤트의 표시 순서가 뒤바뀔 수 있었다(코드리뷰 지적). 오름차순을 직접 정렬해 안정 정렬의
// tie 보존을 그대로 살린다.
export function mergedAuditLogAscending(events: readonly EvidenceEvent[]): EvidenceEvent[] {
  return mergeSeedAndRuntime(events)
    .slice()
    .sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : 0));
}

export function filterAudit(entries: EvidenceEvent[], key: AuditFilterKey): EvidenceEvent[] {
  const filter = AUDIT_FILTERS.find((f) => f.key === key) ?? AUDIT_FILTERS[0];
  return entries.filter((entry) => filter.match(entry.type));
}

// D-3(NEXT_ROADMAP): 케이스 타임라인(CaseWorkbench.CaseTimeline)이 CASE_SHEETS.activity
// 정적 목록만 읽어 행정사 회신·해석 확인 같은 런타임 이벤트가 반영되지 않던 문제 — 관련
// evidenceStore 이벤트를 CaseActivityEntry 모양으로 얹어 정적 activity 앞에 붙인다.
// 실벽시계(evidenceStore.at, ISO)와 데모 고정 시각(activity.at, "오늘 07:58" 표기)은 형식이
// 달라 직접 비교 정렬하지 않는다(D-6 미해결과 동일한 우회 — packageLink.ts의 판단과 같은 원칙:
// 정확한 시각 비교 대신 "발생 여부/순서"만 본다). 런타임 이벤트는 세션 중 방금 일어난 일이므로
// 항상 정적 이력보다 위에 둔다.
const CASE_TIMELINE_EVENT_TYPES: ReadonlySet<EvidenceType> = new Set<EvidenceType>([
  'interpretation_confirmed',
  'package_reply',
]);

const CASE_TIMELINE_OUTCOME: Partial<Record<EvidenceType, CaseActivityEntry['outcome']>> = {
  interpretation_confirmed: 'approved',
  package_reply: 'question',
};

// 코드리뷰(PR #14) P1 교정: evidenceRef("#4791" 등)는 판단 기록 표시 번호일 뿐, 재생 런
// RUN_CONFIGS.runKey와는 별개 채번이다 — 둘이 우연히 겹치지 않는 한(#4788/#4712처럼 정적
// activity에 원래부터 실제 런이 있던 경우만) 일치하지 않는다. 그런데도 runRef를 evidenceRef로
// 그대로 채우면 CaseTimeline이 존재하지 않는 /run/:id로 이동하는 버튼을 만들어, 클릭 시
// RunPage가 config를 못 찾고 loading 화면에 멈춘다. 실제 재생 가능한 runKey가 있을 때만
// 버튼을 만들도록, 여기서 미리 걸러 runRef를 undefined로 남긴다(CaseTimeline은 그대로 텍스트로
// 렌더 — 이미 runRef가 optional인 기존 분기를 그대로 탄다).
const REPLAYABLE_RUN_KEYS = new Set(RUN_CONFIGS.map((config) => config.runKey));

function replayableRunRef(evidenceRef: string | undefined): string | undefined {
  if (!evidenceRef) return undefined;
  return REPLAYABLE_RUN_KEYS.has(evidenceRef.replace('#', '')) ? evidenceRef : undefined;
}

export function caseTimelineActivity(
  caseId: string,
  staticActivity: readonly CaseActivityEntry[],
  events: readonly EvidenceEvent[],
): CaseActivityEntry[] {
  const caseEvents = events.filter((event) => event.caseId === caseId);
  const runtimeEntries: CaseActivityEntry[] = caseEvents
    .filter((event) => CASE_TIMELINE_EVENT_TYPES.has(event.type))
    .map((event) => ({
      runRef: replayableRunRef(event.evidenceRef),
      label: AUDIT_TYPE_LABEL[event.type],
      detail: event.summary ?? '',
      at: '방금',
      outcome: CASE_TIMELINE_OUTCOME[event.type] ?? 'pending',
    }));

  // 코드리뷰 지적: interpretation_confirmed 런타임 이벤트가 붙어도 CASE_SHEETS 정적
  // activity의 "담당자 확인 대기"(outcome:'question') 항목이 그대로 남아 있어, "확인
  // 완료"와 "확인 대기"가 동시에 표시되는 모순이 생겼다 — 정적 항목이 인코딩하는 의미
  // 자체가 "해석 확인 대기 중"이므로, 확인이 실제로 끝나면 그 항목은 제거한다.
  const hasConfirmedInterpretation = caseEvents.some((event) => event.type === 'interpretation_confirmed');
  const filteredStatic = hasConfirmedInterpretation
    ? staticActivity.filter((entry) => entry.outcome !== 'question')
    : staticActivity;

  return [...runtimeEntries, ...filteredStatic];
}

// SD-6(plans/SEED_DESIGN_2026-07-20.md Part B5(c)) — real 모드에서 mock CASE_SHEETS 매치가
// 아예 없는 케이스(진짜 서버 caseId)의 "케이스 타임라인"을 판단 기록(evidenceStore)만으로
// 구성한다. caseTimelineActivity(위)는 mock 정적 activity 위에 특정 런타임 이벤트 2종만
// 얹는 좁은 목적이라 그대로 재사용할 수 없다 — 이 함수는 mock 기반이 아예 없을 때 해당
// 케이스의 판단 기록 전체를 CaseActivityEntry로 승격한다. 재생 가능한 런 단위 서사(mock의
// "#4788 서류요청 준비" 같은 상세 문구)는 없다 — evidence type 단위의 더 거친 신호이고,
// 이는 의도적으로 남겨두는 단순화다(activity 상세가 아니라 "무슨 일이 있었는지 순서"가 목적).
//
// outcome 매핑 근거(4값 'approved'|'pending'|'question'|'replanned'로 24종 EvidenceType을
// 근사): ①승인이 실제로 확정/완료/실행된 것(approval_decided·exported·dispatch_executed·
// delivery_confirmed·interpretation_confirmed·구성원/위임/역할 관리 이벤트 — 관리 조작
// 자체는 그 즉시 완결)은 'approved'. ②아직 진행 중이거나 확정 전(탐지·계획·근거조회·도구실행·
// 요청·검토시작·체크리스트 완료 — 체크리스트 완료는 승인 "직전" 단계라 완료가 아님·응답 초안
// 생성)은 'pending'. ③반려·에스컬레이션처럼 원래 경로가 막혀 다른 조치가 필요해진 경우는
// 'replanned'. ④사람의 추가 확인/응답을 기다리는 안내성 이벤트(행정사 회신)는 'question' —
// 기존 caseTimelineActivity의 CASE_TIMELINE_OUTCOME과 겹치는 두 타입(interpretation_confirmed·
// package_reply)은 그 값('approved'·'question')을 그대로 승계해 두 selector 간 의미가
// 어긋나지 않게 했다.
const CASE_ACTIVITY_OUTCOME: Record<EvidenceType, CaseActivityEntry['outcome']> = {
  intent_classified: 'pending',
  plan_created: 'pending',
  tool_executed: 'pending',
  rag_retrieved: 'pending',
  risk_flagged: 'pending',
  approval_requested: 'pending',
  approval_decided: 'approved',
  approval_rejected: 'replanned',
  review_started: 'pending',
  checklist_completed: 'pending',
  exported: 'approved',
  final_response_generated: 'pending',
  interpretation_confirmed: 'approved',
  role_granted: 'approved',
  role_changed: 'approved',
  member_invited: 'approved',
  member_removed: 'approved',
  delegation_granted: 'approved',
  delegation_revoked: 'approved',
  approval_escalated: 'replanned',
  package_link_issued: 'approved',
  package_link_viewed: 'approved',
  dispatch_executed: 'approved',
  delivery_confirmed: 'approved',
  package_reply: 'question',
  // R3(N02) — 응답이 도착했을 뿐 아직 담당자 해석 확인(interpretation_confirmed) 전이라
  // package_reply와 같은 범주('question' — 사람의 추가 확인/응답을 기다리는 안내성 이벤트).
  worker_reply_received: 'question',
};

// evidence_events.at은 ISO 타임스탬프("2026-07-09T08:00:00Z") — mock activity.at의 상대
// 표기("오늘 07:58")와 형식이 달라 그대로 못 쓴다. 여기선 시:분만 짧게 잘라 보여준다
// (날짜까지 필요한 정밀도는 이 리스트의 목적이 아니다 — CaseHistoryPage처럼 전체 이력을
// 다루는 화면이 아니라 케이스 상세의 최근 활동 요약이라 절대 시각 대신 짧은 표기로 충분).
function shortTimeLabel(iso: string): string {
  return iso.length >= 16 ? iso.slice(11, 16) : iso;
}

export function caseActivityFromEvents(caseId: string, events: readonly EvidenceEvent[]): CaseActivityEntry[] {
  return mergedAuditLog(events)
    .filter((event) => event.caseId === caseId)
    .map((event) => ({
      runRef: replayableRunRef(event.evidenceRef),
      label: AUDIT_TYPE_LABEL[event.type],
      detail: event.summary ?? '',
      at: shortTimeLabel(event.at),
      outcome: CASE_ACTIVITY_OUTCOME[event.type],
    }));
}

// 자동 에스컬레이션(7단계 §3.2) 표면화 — 큐 행의 "승인 지연" Chip이 참조하는 단일 출처.
// 시드+런타임 병합은 mergedAuditLog 하나로 통일했다(D-4, NEXT_ROADMAP — 이 함수와
// CaseHistoryPage.tsx가 각자 같은 병합 로직을 다시 구현하고 있었다, "EVIDENCE_SEED 병합 3벌").
export function isCaseEscalated(caseId: string, events: readonly EvidenceEvent[]): boolean {
  return mergedAuditLog(events).some((e) => e.type === 'approval_escalated' && e.caseId === caseId);
}
