// 배지 색 규칙 테이블 — 1단계 스펙 §0.2 "배지 색 규칙"을 도메인 상태 → BadgeTone 매핑 함수로 정규화.
// Badge 컴포넌트 자체는 도메인 타입을 모른다(rules/frontend.md) — 화면이 여기 함수로 tone을
// 미리 계산해 <Badge tone={...}>에 넘긴다.
import type { ApprovalStatus, CaseState, Severity } from '@/types';

export type BadgeTone = 'critical' | 'warning' | 'pending' | 'info' | 'success' | 'neutral' | 'line';

const SEVERITY_TONE: Record<Severity, BadgeTone> = {
  CRITICAL: 'critical',
  HIGH: 'warning',
  MEDIUM: 'info',
  LOW: 'neutral',
};

export function severityTone(severity: Severity): BadgeTone {
  return SEVERITY_TONE[severity];
}

const APPROVAL_STATUS_TONE: Record<ApprovalStatus, BadgeTone> = {
  pending: 'pending',
  approved: 'success',
  rejected: 'neutral',
  locked: 'pending',
};

export function approvalStatusTone(status: ApprovalStatus): BadgeTone {
  return APPROVAL_STATUS_TONE[status];
}

const CASE_STATE_TONE: Record<CaseState, BadgeTone> = {
  draft: 'neutral',
  risk_review: 'warning',
  approval_pending: 'pending',
  human_approved: 'success',
  completed: 'neutral',
  blocked: 'critical',
};

export function caseStateTone(state: CaseState): BadgeTone {
  return CASE_STATE_TONE[state];
}
