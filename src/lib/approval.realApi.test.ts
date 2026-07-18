import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.4 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

const approveApprovalMock = vi.fn();
const rejectApprovalMock = vi.fn();
const createApprovalRequestMock = vi.fn();
vi.mock('@/lib/api/approvals', () => ({
  approveApproval: (...args: unknown[]) => approveApprovalMock(...args),
  rejectApproval: (...args: unknown[]) => rejectApprovalMock(...args),
  createApprovalRequest: (...args: unknown[]) => createApprovalRequestMock(...args),
}));

const fetchEvidenceMock = vi.fn();
const createEvidenceEventMock = vi.fn().mockResolvedValue(undefined);
vi.mock('@/lib/api/evidence', () => ({
  fetchEvidence: (...args: unknown[]) => fetchEvidenceMock(...args),
  createEvidenceEvent: (...args: unknown[]) => createEvidenceEventMock(...args),
}));

import { useApprovalActions } from './approval';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CaseCard } from '@/types';

function makeCard(overrides: Partial<CaseCard> = {}): CaseCard {
  return {
    caseId: 'cs1',
    caseCode: 'case_001',
    title: '테스트 케이스',
    severity: 'HIGH',
    state: 'approval_pending',
    approvalRequired: true,
    primaryAction: { actionId: 'act1', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
    secondaryAction: { actionId: 'act1-detail', label: '상세', state: 'ready', requiresApproval: false, kind: 'detail' },
    preparedBy: 'rule',
    ...overrides,
  };
}

describe('useApprovalActions — real 모드(R2.4)', () => {
  afterEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
    approveApprovalMock.mockReset();
    rejectApprovalMock.mockReset();
    createApprovalRequestMock.mockReset();
    fetchEvidenceMock.mockReset();
    createEvidenceEventMock.mockReset().mockResolvedValue(undefined);
  });

  it('approve는 서버 확인 후에만 로컬 approvalStore/caseStore를 미러링한다(낙관적 갱신 금지, GOTCHAS §2)', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);
    approveApprovalMock.mockResolvedValue({ caseState: 'human_approved' });
    fetchEvidenceMock.mockResolvedValue([]);

    const { result } = renderHook(() => useApprovalActions());
    const ok = await result.current.approve({ card, usableCount: 1, approvalId: 'apv1', pin: '1234' });

    expect(ok).toBe(true);
    expect(approveApprovalMock).toHaveBeenCalledWith(
      'apv1',
      expect.objectContaining({ identityMethod: 'pin', pin: '1234' }),
    );
    expect(useApprovalStore.getState().approvals['act1']?.status).toBe('approved');
    expect(useCaseStore.getState().cases.cs1.state).toBe('human_approved');
  });

  it('approve는 서버가 이미 남긴 결정 evidence를 로컬에 다시 append하지 않고, 재조회로 동기화한다', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);
    approveApprovalMock.mockResolvedValue({ caseState: 'human_approved' });
    fetchEvidenceMock.mockResolvedValue([
      { id: 'server-evt-1', type: 'approval_decided', at: '2026-07-17T00:00:00Z', summary: '승인 완료' },
    ]);

    const { result } = renderHook(() => useApprovalActions());
    await result.current.approve({ card, usableCount: 1, approvalId: 'apv1', pin: '1234' });

    // checklist_completed는 로컬에서 낙관적으로 남지만, approval_decided는 로컬에서 만들지 않는다.
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'checklist_completed')).toBe(true);
    expect(
      useEvidenceStore.getState().events.some((e) => e.id === 'act1-approved' && e.type === 'approval_decided'),
    ).toBe(false);
    await waitFor(() =>
      expect(useEvidenceStore.getState().events.some((e) => e.id === 'server-evt-1')).toBe(true),
    );
  });

  it('approve는 approvalId 없이는 서버를 호출하지 않고 false를 반환한다', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);

    const { result } = renderHook(() => useApprovalActions());
    const ok = await result.current.approve({ card, usableCount: 1, pin: '1234' });

    expect(ok).toBe(false);
    expect(approveApprovalMock).not.toHaveBeenCalled();
  });

  it('approve는 서버 에러(ApiError)를 그대로 전파한다(화면이 PIN 에러로 표면화)', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);
    approveApprovalMock.mockRejectedValue(new Error('PIN이 일치하지 않습니다'));

    const { result } = renderHook(() => useApprovalActions());
    await expect(result.current.approve({ card, usableCount: 1, approvalId: 'apv1', pin: '9999' })).rejects.toThrow(
      'PIN이 일치하지 않습니다',
    );
    // 실패했으므로 로컬 상태는 그대로(승인되지 않음) — 낙관적 갱신 금지 확인.
    expect(useCaseStore.getState().cases.cs1.state).toBe('approval_pending');
  });

  it('reject는 사유가 비어 있으면 서버를 호출하지 않고 false를 반환한다(DB 정본 요구사항 선반영)', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);

    const { result } = renderHook(() => useApprovalActions());
    const ok = await result.current.reject({ card, usableCount: 1, reason: '   ', approvalId: 'apv1', pin: '1234' });

    expect(ok).toBe(false);
    expect(rejectApprovalMock).not.toHaveBeenCalled();
  });

  it('reject 성공 시 서버 확인 후 케이스를 returned로 미러링한다', async () => {
    const card = makeCard();
    useCaseStore.getState().upsert(card);
    rejectApprovalMock.mockResolvedValue({ caseState: 'returned' });
    fetchEvidenceMock.mockResolvedValue([]);

    const { result } = renderHook(() => useApprovalActions());
    const ok = await result.current.reject({ card, usableCount: 1, reason: '근거 부족', approvalId: 'apv1', pin: '1234' });

    expect(ok).toBe(true);
    expect(useCaseStore.getState().cases.cs1.state).toBe('returned');
    expect(useApprovalStore.getState().approvals['act1']?.status).toBe('rejected');
  });

  it('requestOwnerApproval은 real 모드에서 서버에 승인 요청을 생성한다', async () => {
    const card = makeCard();
    createApprovalRequestMock.mockResolvedValue({ approvalId: 'apv_new', caseState: 'approval_pending' });
    fetchEvidenceMock.mockResolvedValue([]);

    const { result } = renderHook(() => useApprovalActions());
    await result.current.requestOwnerApproval(card);

    expect(createApprovalRequestMock).toHaveBeenCalledWith('act1');
  });

  it('reopenForReview은 real 모드에서 서버 승인 요청 생성 후 로컬을 approval_pending으로 되돌린다', async () => {
    const card = makeCard({ state: 'returned' });
    useCaseStore.getState().upsert(card);
    createApprovalRequestMock.mockResolvedValue({ approvalId: 'apv_new', caseState: 'approval_pending' });

    const { result } = renderHook(() => useApprovalActions());
    await result.current.reopenForReview(card);

    expect(createApprovalRequestMock).toHaveBeenCalledWith('act1');
    expect(useCaseStore.getState().cases.cs1.state).toBe('approval_pending');
  });
});
