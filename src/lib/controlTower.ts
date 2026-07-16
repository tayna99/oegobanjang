import { usableCitations } from '@/stores/citationStore';
import type { CaseCard, Severity } from '@/types';
import type { CaseSheet } from '@/mocks/fixtures';

// PC 컨트롤 타워(§3a) KPI·추이 파생 — reference/design-system/외고반장 PC.dc.html §3a(93~114행).
// KPI는 활성 케이스에서 파생(디자인 값과 일치). 지난주 추이·오늘 델타는 파생 불가한 mock.

export interface ControlTowerKpis {
  activeCases: number; // 활성 케이스
  highRisk: number; // 고위험 (C+H)
  dDayImminent: number; // D-day 임박 (≤7일)
  evidenceShort: number; // 근거 부족 — 승인 필요한데 실사용 근거 0건(§3c 잠금 대상)
}

const IMMINENT_DAYS = 7;

export function controlTowerKpis(cards: CaseCard[], sheets: Record<string, CaseSheet>): ControlTowerKpis {
  const isHighRisk = (s: Severity) => s === 'CRITICAL' || s === 'HIGH';
  return {
    activeCases: cards.length,
    highRisk: cards.filter((c) => isHighRisk(c.severity)).length,
    // ≤7일(경과 D+ 포함). undefined(모니터링 등)는 제외.
    dDayImminent: cards.filter((c) => c.dDay !== undefined && c.dDay <= IMMINENT_DAYS).length,
    // 승인이 필요한데 실사용 근거가 0건 → missing_evidence=true로 승인 잠김(§3c 가드레일).
    // 초기 단계(감지·수집) 케이스는 아직 승인 대상이 아니므로 세지 않는다 → 디자인 "근거 부족 0"과 일치.
    evidenceShort: cards.filter(
      (c) => c.approvalRequired && usableCitations(sheets[c.caseId]?.citations ?? []).length === 0,
    ).length,
  };
}

// 파이프라인 타일 델타 문구(§3a 71~88행) — "오늘 신규" 값은 파생 불가한 데모 mock.
export const PIPELINE_DELTAS = {
  detected: '+2 오늘',
  collecting: '+1',
  drafted: '+1',
  awaitingApproval: '내 처리 필요',
  executedWeekly: 'mock 발송',
} as const;

// 활성 케이스 추이 7일(§3a 112행 polyline) — 지난주 이력이라 파생 불가한 mock 시계열.
export const WEEKLY_ACTIVE_TREND = [3, 4, 4, 5, 5, 5, 6] as const;
export const WEEKLY_TREND_RANGE = '7/4 – 7/10';

// 우선 처리 케이스 행 액션 — 디자인 §3a 132~191행 + C10 교정(고위험은 "검토", 처리 버튼 금지).
export type RowActionKind = 'review' | 'approve' | 'view';

export function rowAction(card: CaseCard): { kind: RowActionKind; label: string } {
  // 고위험(기한 경과 blocked)은 앱 승인 경로가 아니라 검토→행정사 전달 전용(GOTCHAS 고위험 처리 버튼 금지).
  if (card.state === 'blocked') return { kind: 'review', label: '검토' };
  if (card.state === 'approval_pending') return { kind: 'approve', label: '승인' };
  return { kind: 'view', label: '보기' };
}
