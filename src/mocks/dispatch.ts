// 발송 실행 큐(PC 4d) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html
// §4d(349~444행) 이식. "승인된 것만 이 화면에 도착 · mock dispatch · 실행도 evidence 기록."
// 각본 기반 고정 목데이터(RunEngine·EVIDENCE_SEED와 동일 철학) — 실제 승인 파이프라인
// (ApprovalStore/CaseStore)에 자동으로 연결하지 않는다(승인 완료→큐 자동 반영은 후속 확장,
// 이번엔 "큐에 있는 항목을 실행하면 evidence가 남는다"는 실행 규칙만 시연한다).
export type DispatchActionKind = 'dispatch' | 'link_issue';

export interface DispatchItem {
  id: string;
  caseId?: string;
  workerName: string;
  actionLabel: string;
  channel: string;
  evidenceRef: string;
  approvedAt: string;
  approvedBy: string;
  actionKind: DispatchActionKind;
  // approvalStore.approvals의 키 — 이 큐가 "승인된 것만 도착"을 실제로 강제하려면
  // 화면이 approvalStore.dispatch(actionId)를 거쳐야 한다(코드리뷰 P1, GOTCHAS "승인 없이
  // dispatch 불가"와 동일 가드레일). mock 시나리오상 항상 승인된 채로 시작하지만, 그 보장을
  // approvalStore가 실제로 지키게 한다.
  actionId: string;
}

export const DISPATCH_QUEUE: DispatchItem[] = [
  {
    id: 'evt-4789',
    caseId: 'nguyen',
    workerName: 'Nguyen Van A',
    actionLabel: '서류요청 메시지 발송 (VN)',
    channel: 'Zalo',
    evidenceRef: '#4789',
    approvedAt: '07/10 09:32',
    approvedBy: '김담당 (본인)',
    actionKind: 'dispatch',
    actionId: 'nguyen-dispatch-4789',
  },
  {
    id: 'evt-4791',
    caseId: 'siti',
    workerName: 'Siti R.',
    actionLabel: '신고 준비 확인 요청 (ID)',
    channel: 'SMS',
    evidenceRef: '#4791',
    approvedAt: '07/10 09:41',
    approvedBy: '김담당 (본인)',
    actionKind: 'dispatch',
    actionId: 'siti-dispatch-4791',
  },
  {
    id: 'evt-4792',
    caseId: 'batbayar',
    workerName: 'Batbayar E.',
    actionLabel: '행정사 검토 패키지 전달',
    channel: '만료형 링크',
    evidenceRef: '#4792',
    approvedAt: '07/10 09:45',
    approvedBy: '사장님 (owner)',
    actionKind: 'link_issue',
    actionId: 'batbayar-link-4792',
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
