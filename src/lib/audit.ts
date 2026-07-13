import type { ChipTone } from '@/lib/chipTone';
import type { EvidenceEvent, EvidenceType } from '@/types';
import { EVIDENCE_SEED } from '@/mocks/evidence';

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

// 시드(앱 열기 전 기록) + 런타임 이벤트를 병합해 최신순 정렬. id 중복은 런타임 우선.
// 스토어 자체는 비어 시작하므로(evidenceStore) 시드는 표시 시점에 합친다(블루프린트 §9-A, M8도 동일).
export function mergedAuditLog(events: readonly EvidenceEvent[]): EvidenceEvent[] {
  const runtimeIds = new Set(events.map((event) => event.id));
  const combined = [...EVIDENCE_SEED.filter((event) => !runtimeIds.has(event.id)), ...events];
  return combined.slice().sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
}

export function filterAudit(entries: EvidenceEvent[], key: AuditFilterKey): EvidenceEvent[] {
  const filter = AUDIT_FILTERS.find((f) => f.key === key) ?? AUDIT_FILTERS[0];
  return entries.filter((entry) => filter.match(entry.type));
}

// 자동 에스컬레이션(7단계 §3.2) 표면화 — 큐 행의 "승인 지연" Chip이 참조하는 단일 출처.
// 시드+런타임을 모두 보는 mergedAuditLog와 달리 여기선 원시 이벤트 배열만 받으면 되므로
// 호출부가 이미 병합된 목록이든 evidenceStore 원본이든 그대로 넘길 수 있게 유연하게 둔다.
export function isCaseEscalated(caseId: string, events: readonly EvidenceEvent[]): boolean {
  const runtimeIds = new Set(events.map((e) => e.id));
  const combined = [...EVIDENCE_SEED.filter((e) => !runtimeIds.has(e.id)), ...events];
  return combined.some((e) => e.type === 'approval_escalated' && e.caseId === caseId);
}
