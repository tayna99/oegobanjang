import { DISPATCH_CATALOG, type DispatchCatalogEntry } from '@/mocks/dispatch';
import type { Approval, EvidenceEvent } from '@/types';

export interface DispatchQueueItem extends DispatchCatalogEntry {
  evidenceRef: string;
  approvedAt: string;
  approvedBy: string;
}

// 승인 완료 → 발송 큐 자동 연동(R1.4, NEXT_ROADMAP 1.4) — "승인된 것만 이 화면에 도착"을
// approvalStore가 실제로 강제한다. 카탈로그 항목은 실제 승인 액션(actionId)이 approved 상태일
// 때만, 그리고 아직 실행(dispatch_executed)되지 않았을 때만 큐에 나타난다. batbayar처럼
// caseStore 상태 전이가 없는(blocked 종착, 패키지 내보내기 승인) 항목도 같은 규칙으로
// 다룬다 — 큐의 진실은 caseStore.state가 아니라 approvalStore(dispatch()가 실제로 검사하는
// 그 상태)다.
export function deriveDispatchQueue(
  approvals: Record<string, Approval>,
  events: readonly EvidenceEvent[],
): DispatchQueueItem[] {
  return DISPATCH_CATALOG.flatMap((entry) => {
    if (approvals[entry.actionId]?.status !== 'approved') return [];
    const alreadyExecuted = events.some((e) => e.type === 'dispatch_executed' && e.actionId === entry.actionId);
    if (alreadyExecuted) return [];
    const decided = events.find((e) => e.type === 'approval_decided' && e.actionId === entry.actionId);
    return [
      {
        ...entry,
        evidenceRef: decided?.evidenceRef ?? entry.fallbackEvidenceRef,
        // 실벽시계(런타임 evidence.at)와 데모 고정 시각 표기를 직접 비교·포맷하지 않는다
        // (D-6과 동일한 판단 — CaseWorkbench.caseTimelineActivity의 '방금' 표기 참고).
        approvedAt: decided ? '방금' : entry.fallbackApprovedAt,
        approvedBy: decided?.actor ?? entry.fallbackApprovedBy,
      },
    ];
  });
}
