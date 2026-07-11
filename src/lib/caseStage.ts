// PC 워크벤치 "진행 개요" 스테퍼(디자인 §3b)와 "승인/전달 상태" 미니 스테퍼의
// 단계 파생 — reference/design-system/외고반장 PC.dc.html 335~343행(스테퍼),
// 418~426행(전달 상태). 단계는 CaseState + 근거 유무에서 결정적으로 파생한다.
// 새 단계·라벨을 임의로 추가하지 말 것(임의값 금지 — 디자인 원문 라벨 그대로).
import type { CaseCard } from '@/types';
import type { CaseSheet } from '@/mocks/fixtures';

export const CASE_STAGES = ['감지', '근거 수집', '초안 생성', '승인 대기', '실행 (mock)'] as const;

// 현재 단계 인덱스. 인덱스보다 앞 단계는 완료로 표시한다.
// completed만 마지막 단계 "완료"로 취급한다 — 발송은 승인 기반 mock이므로
// "실행 (mock)"이 완료 표시되는 경우는 없다(AGENTS §8: 실제 발송 없음).
export function caseStageIndex(card: CaseCard, sheet?: CaseSheet): number {
  switch (card.state) {
    case 'completed':
    case 'human_approved':
      return 4;
    case 'approval_pending':
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
    case 'blocked':
      return 1;
    default:
      return 0;
  }
}
