import { caseGroupFor } from '@/lib/cases';
import type { CaseCard, EvidenceEvent } from '@/types';

export interface MonthlyReport {
  processedCases: number;
  proactiveDetected: number;
  proactivePercent: number;
  unauthorizedSendCount: number;
}

// 사장님 PC 최소화면(4f) 월간 리포트 — MONTHLY_REPORT 하드코딩을 스토어 파생값으로
// 대체한다(R1.8, NEXT_ROADMAP 1.8 "KPI=스토어 파생값" 원칙, 2.5.6과 동일 원칙).
// 평균 승인 소요 시간은 여기 포함하지 않는다 — 시드 evidence의 고정 데모 시각과 런타임
// evidence의 실벽시계를 직접 빼면 D-6(실벽시계 vs 데모 날짜 혼용, 아직 미해결)과 같은
// 왜곡값이 나온다(2.5.6이 파이프라인 델타·주간 추이를 같은 이유로 mock으로 남긴 것과
// 동일 판단 — OwnerHomeWorkbench가 그 두 필드만 별도 mock 상수로 유지한다).
export function deriveMonthlyReport(cards: CaseCard[], events: readonly EvidenceEvent[]): MonthlyReport {
  const processed = cards.filter((card) => caseGroupFor(card) === 'completed');
  const proactiveDetected = processed.filter((card) => card.preparedBy === 'agent').length;

  // 승인 없는 외부 발송 — approvalStore.dispatch()가 구조적으로 차단하므로 항상 0이어야
  // 한다(GOTCHAS §1). 하드코딩된 "0"이 아니라 evidence에서 실제로 세어, 가드레일이
  // 뚫리면 이 화면도 그 사실을 드러내게 한다.
  const unauthorizedSendCount = events.filter(
    (event) =>
      event.type === 'dispatch_executed' &&
      !events.some((decided) => decided.type === 'approval_decided' && decided.actionId === event.actionId),
  ).length;

  return {
    processedCases: processed.length,
    proactiveDetected,
    proactivePercent: processed.length > 0 ? Math.round((proactiveDetected / processed.length) * 100) : 0,
    unauthorizedSendCount,
  };
}
