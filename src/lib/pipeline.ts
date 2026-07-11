// 파이프라인 집계 — 디자인 §2a 스탯 로우·§3a 타일(블루프린트 §3, M2.6.1/2.5.6 공용).
// 값은 누적 깔때기: "감지 6 · 근거 수집 5 · 초안 4 · 승인 대기 3"은 각 단계까지
// 도달한 케이스 수다. agentStage(카드 필드)에서 결정적으로 파생한다.
import type { AgentStage, CaseCard } from '@/types';

const STAGE_ORDER: Record<AgentStage, number> = {
  detected: 0,
  collecting: 1,
  drafted: 2,
  awaiting_approval: 3,
  executed: 4,
};

export interface PipelineCounts {
  detected: number;
  collecting: number;
  drafted: number;
  awaitingApproval: number;
}

export function pipelineCounts(cards: CaseCard[]): PipelineCounts {
  const reached = (threshold: number) =>
    cards.filter((card) => STAGE_ORDER[card.agentStage ?? 'detected'] >= threshold).length;
  return {
    detected: reached(0),
    collecting: reached(1),
    drafted: reached(2),
    awaitingApproval: reached(3),
  };
}
