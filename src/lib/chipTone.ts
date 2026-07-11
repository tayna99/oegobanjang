// Chip 색 규칙 테이블 — 1단계 스펙 §0.2 "배지 색 규칙"을 도메인 상태 → ChipTone 매핑 함수로 정규화.
// Chip 컴포넌트 자체는 도메인 타입을 모른다(rules/frontend.md) — 화면이 여기 함수로 tone을
// 미리 계산해 <Chip tone={...}>에 넘긴다.
//
// v1(badgeTone)에서 새로 짬(2026-07-11, M2.5.2) — 이름만 보고 값을 옮기면 안 되는 이유:
// v1은 pending(amber, "승인 대기") / info(blue, MEDIUM severity)였지만 Montage v2는
// "승인 필요"를 블루로, MEDIUM을 흐린 오렌지로 정의한다(정반대). 그래서 'pending'/'info'라는
// 모호한 이름 자체를 없애고 색상표(rules/design.md §5)의 실제 의미대로 새 이름을 붙였다:
//   critical=위험(빨강) / high=우선(진한 오렌지) / medium=확인(흐린 오렌지)
//   / positive=완료(초록) / approval=승인 필요(블루) / neutral=중립(회색) / line=아웃라인
import type { AgentStage, ApprovalStatus, CaseState, Severity } from '@/types';

// draft(보라)·detected(시안)는 2.5.4b에서 추가된 파이프라인 단계 톤(디자인 §3a/§2a).
export type ChipTone =
  | 'critical'
  | 'high'
  | 'medium'
  | 'positive'
  | 'approval'
  | 'draft'
  | 'detected'
  | 'neutral'
  | 'line';

const SEVERITY_TONE: Record<Severity, ChipTone> = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'neutral',
};

export function severityTone(severity: Severity): ChipTone {
  return SEVERITY_TONE[severity];
}

const APPROVAL_STATUS_TONE: Record<ApprovalStatus, ChipTone> = {
  pending: 'approval',
  approved: 'positive',
  rejected: 'neutral',
  locked: 'approval',
};

export function approvalStatusTone(status: ApprovalStatus): ChipTone {
  return APPROVAL_STATUS_TONE[status];
}

const CASE_STATE_TONE: Record<CaseState, ChipTone> = {
  draft: 'neutral',
  risk_review: 'high',
  approval_pending: 'approval',
  returned: 'high', // 반려 — 보완 필요 경고 톤(Mobile §2c, 2.5.4b)
  human_approved: 'positive',
  completed: 'neutral',
  blocked: 'critical',
};

export function caseStateTone(state: CaseState): ChipTone {
  return CASE_STATE_TONE[state];
}

// 파이프라인 단계 → 칩 톤 (디자인 §3a 타일·큐 컬럼 색): 감지=시안, 수집=블루(approval과
// 동일 페어), 초안=보라, 승인 대기=오렌지(high), 실행=초록.
const AGENT_STAGE_TONE: Record<AgentStage, ChipTone> = {
  detected: 'detected',
  collecting: 'approval',
  drafted: 'draft',
  awaiting_approval: 'high',
  executed: 'positive',
};

export function agentStageTone(stage: AgentStage): ChipTone {
  return AGENT_STAGE_TONE[stage];
}
