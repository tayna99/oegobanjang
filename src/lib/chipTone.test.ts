import { describe, expect, it } from 'vitest';
import type { ApprovalStatus, CaseState, Severity } from '@/types';
import { approvalStatusTone, caseStateTone, severityTone } from './chipTone';

describe('severityTone — 위험도 Chip 색 규칙 (스펙 §0.2, v2 색상표 rules/design.md §5)', () => {
  it.each([
    ['CRITICAL', 'critical'],
    ['HIGH', 'high'],
    ['MEDIUM', 'medium'],
    ['LOW', 'neutral'],
  ] as [Severity, ReturnType<typeof severityTone>][])('%s → %s', (severity, tone) => {
    expect(severityTone(severity)).toBe(tone);
  });
});

describe('approvalStatusTone — 승인 상태 Chip 색 규칙', () => {
  it.each([
    ['pending', 'approval'],
    ['approved', 'positive'],
    ['rejected', 'neutral'],
    ['locked', 'approval'],
  ] as [ApprovalStatus, ReturnType<typeof approvalStatusTone>][])('%s → %s', (status, tone) => {
    expect(approvalStatusTone(status)).toBe(tone);
  });
});

describe('caseStateTone — 케이스 상태 Chip 색 규칙', () => {
  it.each([
    ['risk_review', 'high'],
    ['approval_pending', 'approval'],
    ['human_approved', 'positive'],
    ['completed', 'neutral'],
    ['blocked', 'critical'],
  ] as [CaseState, ReturnType<typeof caseStateTone>][])('%s → %s', (state, tone) => {
    expect(caseStateTone(state)).toBe(tone);
  });

  it("'draft'는 스펙 표에 없는 초기 상태 — neutral로 처리", () => {
    expect(caseStateTone('draft')).toBe('neutral');
  });
});
