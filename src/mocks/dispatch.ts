// 발송 실행 큐(PC 4d) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html
// §4d(349~444행) 이식. "승인된 것만 이 화면에 도착 · mock dispatch · 실행도 evidence 기록."
// R1.4(NEXT_ROADMAP 1.4) — 큐 자체는 더 이상 고정 각본이 아니라 실제 승인 파이프라인
// (approvalStore)에서 파생한다(src/lib/dispatch.ts deriveDispatchQueue). 여기 남는 건
// 화면에 필요한 표시용 카탈로그(누가·무엇을·어느 채널로)뿐 — actionId는 각 화면의 실제
// 승인 액션 id를 그대로 쓴다(approvalStore/caseStore와 별개 id를 발명하지 않는다,
// "actionId 체계 통일").
export type DispatchActionKind = 'dispatch' | 'link_issue';

export interface DispatchCatalogEntry {
  id: string;
  caseId?: string;
  workerName: string;
  actionLabel: string;
  channel: string;
  actionKind: DispatchActionKind;
  actionId: string;
  // approval_decided evidence를 찾지 못했을 때만 쓰는 표시용 기본값 — batbayar 패키지
  // 내보내기 승인(PackagePage)은 애초에 approval_decided를 남기지 않아 항상 이 경로를 타고,
  // 나머지는 테스트가 evidence 없이 approvalStore만 직접 세팅한 경우에 쓰인다.
  fallbackEvidenceRef: string;
  fallbackApprovedAt: string;
  fallbackApprovedBy: string;
}

export const DISPATCH_CATALOG: DispatchCatalogEntry[] = [
  {
    id: 'evt-4789',
    caseId: 'nguyen',
    workerName: 'Nguyen Van A',
    actionLabel: '서류요청 메시지 발송 (VN)',
    channel: 'Zalo',
    actionKind: 'dispatch',
    actionId: 'nguyen-approve',
    fallbackEvidenceRef: '#4789',
    fallbackApprovedAt: '07/10 09:32',
    fallbackApprovedBy: '김담당 (본인)',
  },
  {
    id: 'evt-4791',
    caseId: 'siti',
    workerName: 'Siti R.',
    actionLabel: '신고 준비 확인 요청 (ID)',
    channel: 'SMS',
    actionKind: 'dispatch',
    actionId: 'siti-approve',
    fallbackEvidenceRef: '#4791',
    fallbackApprovedAt: '07/10 09:41',
    fallbackApprovedBy: '김담당 (본인)',
  },
  {
    id: 'evt-4792',
    caseId: 'batbayar',
    workerName: 'Batbayar E.',
    actionLabel: '행정사 검토 패키지 전달',
    channel: '만료형 링크',
    actionKind: 'link_issue',
    actionId: 'batbayar-handoff-export',
    fallbackEvidenceRef: '#4792',
    fallbackApprovedAt: '07/10 09:45',
    fallbackApprovedBy: '사장님 (owner)',
  },
];

export interface DispatchHistoryItem {
  id: string;
  workerName: string;
  actionLabel: string;
  channel: string;
  evidenceRef: string;
  timeline: string; // "07/09 16:02 승인 · 07/10 08:30 실행"
  outcome: string; // "실행 완료 · 전달됨" | "실행 완료 · 응답 수신"
}

export const DISPATCH_HISTORY: DispatchHistoryItem[] = [
  {
    id: 'evt-4770',
    workerName: 'Pham Duc M.',
    actionLabel: '서류 리마인드 (VN)',
    channel: 'Zalo',
    evidenceRef: '#4770',
    timeline: '07/09 16:02 승인 · 07/10 08:30 실행',
    outcome: '실행 완료 · 전달됨',
  },
  {
    id: 'evt-4789-history',
    workerName: 'Nguyen Van A',
    actionLabel: '서류요청 1차 (VN)',
    channel: 'Zalo',
    evidenceRef: '#4789',
    timeline: '07/10 09:32 승인 · 09:35 실행',
    outcome: '실행 완료 · 응답 수신',
  },
];
