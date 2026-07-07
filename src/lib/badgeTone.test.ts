import { describe, expect, it } from 'vitest';
import type { ApprovalStatus, CaseState, Severity } from '@/types';
import { approvalStatusTone, caseStateTone, severityTone } from './badgeTone';

describe('severityTone — 위험도 배지 색 규칙 (스펙 §0.2)', () => {
  it.each([
    ['CRITICAL', 'critical'],
    ['HIGH', 'warning'],
    ['MEDIUM', 'info'],
    ['LOW', 'neutral'],
  ] as [Severity, ReturnType<typeof severityTone>][])('%s → %s', (severity, tone) => {
    expect(severityTone(severity)).toBe(tone);
  });
});

describe('approvalStatusTone — 승인 상태 배지 색 규칙 (스펙 §0.2)', () => {
  it.each([
    ['pending', 'pending'],
    ['approved', 'success'],
    ['rejected', 'neutral'],
    ['locked', 'pending'],
  ] as [ApprovalStatus, ReturnType<typeof approvalStatusTone>][])('%s → %s', (status, tone) => {
    expect(approvalStatusTone(status)).toBe(tone);
  });
});

describe('caseStateTone — 케이스 상태 배지 색 규칙 (스펙 §0.2)', () => {
  it.each([
    ['risk_review', 'warning'],
    ['approval_pending', 'pending'],
    ['human_approved', 'success'],
    ['completed', 'neutral'],
    ['blocked', 'critical'],
  ] as [CaseState, ReturnType<typeof caseStateTone>][])('%s → %s', (state, tone) => {
    expect(caseStateTone(state)).toBe(tone);
  });

  it("'draft'는 스펙 표에 없는 초기 상태 — neutral로 처리", () => {
    expect(caseStateTone('draft')).toBe('neutral');
  });
});
