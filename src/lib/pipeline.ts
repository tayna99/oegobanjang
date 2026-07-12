// 파이프라인 집계 — 디자인 §2a 스탯 로우·§3a 타일(블루프린트 §3, M2.6.1/2.5.6 공용).
// 값은 누적 깔때기: "감지 6 · 근거 수집 5 · 초안 4 · 승인 대기 3"은 각 단계까지
// 도달한 케이스 수다. agentStage(카드 필드)에서 결정적으로 파생한다.
import type { AgentStage, CaseCard } from '@/types';
import { EXECUTED_WEEKLY_MOCK } from '@/mocks/fixtures';

const STAGE_ORDER: Record<AgentStage, number> = {
  detected: 0,
  collecting: 1,
  drafted: 2,
  awaiting_approval: 3,
  executed: 4,
};

// 5단계 전부 반환(코드리뷰 F4 교정: 선택자가 마지막 단계를 빼놓아 각 화면이 상수를 따로
// 스티칭하던 것을 통합). executedWeekly는 활성 케이스에서 파생 불가한 지난주 mock 값.
export interface PipelineStats {
  detected: number;
  collecting: number;
  drafted: number;
  awaitingApproval: number;
  executedWeekly: number;
}

export function pipelineStats(cards: CaseCard[]): PipelineStats {
  const reached = (threshold: number) =>
    cards.filter((card) => STAGE_ORDER[card.agentStage ?? 'detected'] >= threshold).length;
  return {
    detected: reached(0),
    collecting: reached(1),
    drafted: reached(2),
    awaitingApproval: reached(3),
    executedWeekly: EXECUTED_WEEKLY_MOCK,
  };
}
