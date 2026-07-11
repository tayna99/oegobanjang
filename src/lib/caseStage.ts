// PC 워크벤치 "진행 개요" 스테퍼(디자인 §3b)와 "승인/전달 상태" 미니 스테퍼의
// 단계 파생 — reference/design-system/외고반장 PC.dc.html 335~343행(스테퍼),
// 418~426행(전달 상태). 단계는 CaseState + 근거 유무에서 결정적으로 파생한다.
// 새 단계·라벨을 임의로 추가하지 말 것(임의값 금지 — 디자인 원문 라벨 그대로).
import type { AgentStage, CaseCard } from '@/types';
import type { CaseSheet } from '@/mocks/fixtures';

export const CASE_STAGES = ['감지', '근거 수집', '초안 생성', '승인 대기', '실행 (mock)'] as const;

// 파이프라인 단계 라벨 — 디자인 §3a 타일·§2a 스탯 로우 어휘(블루프린트 §3).
// CASE_STAGES(워크벤치 스테퍼)와 표기가 다른 것은 디자인 원문이 다르기 때문 — 임의 통일 금지.
export const AGENT_STAGE_LABELS: Record<AgentStage, string> = {
  detected: '감지됨',
  collecting: '근거 수집 중',
  drafted: '초안 생성 완료',
  awaiting_approval: '승인 대기',
  executed: '실행 완료',
};

const AGENT_STAGE_INDEX: Record<AgentStage, number> = {
  detected: 0,
  collecting: 1,
  drafted: 2,
  awaiting_approval: 3,
  executed: 4,
};

// 현재 단계 인덱스. 인덱스보다 앞 단계는 완료로 표시한다.
// card.agentStage(2.5.4b 파운데이션 필드)가 있으면 그것이 진실이고,
// 없으면 상태에서 파생한다. completed만 마지막 단계 "완료"로 취급한다 —
// 발송은 승인 기반 mock이므로 "실행 (mock)"이 완료 표시되는 경우는 없다(AGENTS §8).
export function caseStageIndex(card: CaseCard, sheet?: CaseSheet): number {
  if (card.agentStage) return AGENT_STAGE_INDEX[card.agentStage];
  switch (card.state) {
    case 'completed':
    case 'human_approved':
      return 4;
    case 'approval_pending':
    case 'returned':
    case 'blocked':
      return 3;
    default:
      // draft / risk_review: 근거가 연결됐으면 초안 생성 단계, 아니면 근거 수집 단계.
      return sheet && sheet.citations.length > 0 ? 2 : 1;
  }
}

export const DELIVERY_STAGES = ['준비됨', '승인 대기', '승인 완료', '발송 (mock)'] as const;

// 우측 레일 "승인 / 전달 상태" 현재 인덱스. completed여도 "발송 (mock)"은
// 도달하지 않는다 — 이 MVP는 발송을 실행하지 않는다(고정 가드레일).
export function deliveryStageIndex(card: CaseCard): number {
  switch (card.state) {
    case 'completed':
    case 'human_approved':
      return 2;
    case 'approval_pending':
    case 'returned':
    case 'blocked':
      return 1;
    default:
      return 0;
  }
}
