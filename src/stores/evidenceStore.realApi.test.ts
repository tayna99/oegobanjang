import { waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.5 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { useEvidenceStore } from './evidenceStore';
import type { EvidenceEvent } from '@/types';

function jsonResponse(body: unknown, status = 201): Response {
  return new Response(JSON.stringify(body), { status });
}

// 코드리뷰 회귀(PR #20 P1): 기본 type은 반드시 서버로 실제 POST가 시도되는(=특권/무인증
// 제외 목록 밖) 타입이어야 한다 — role_granted를 기본값으로 쓰면 아래 "서버 기록 실패" 등의
// 테스트가 fetch 호출 자체를 검증하지 못한 채 통과해버린다(PRIVILEGED_EVIDENCE_TYPES는
// POST 시도 자체를 건너뛰므로).
function makeEvent(overrides: Partial<EvidenceEvent> = {}): EvidenceEvent {
  return { id: 'e1', type: 'plan_created', at: '2026-07-17T09:00:00Z', summary: '계획 생성', ...overrides };
}

describe('evidenceStore — real 모드(R2.5)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('append는 로컬 상태를 먼저 낙관적으로 갱신한다(네트워크 완료를 기다리지 않음)', () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse({})) as unknown as typeof fetch;
    useEvidenceStore.getState().append(makeEvent());
    expect(useEvidenceStore.getState().events).toHaveLength(1);
  });

  it('일반 타입은 POST /api/v1/evidence로 서버에 기록한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    global.fetch = fetchMock as unknown as typeof fetch;

    useEvidenceStore.getState().append(makeEvent({ type: 'interpretation_confirmed', caseId: 'nguyen' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/evidence',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ type: 'interpretation_confirmed', case_id: 'nguyen', summary: '계획 생성' }),
      }),
    );
  });

  it.each(['package_link_issued', 'package_link_viewed', 'package_reply'] as const)(
    '%s는 무인증 패키지 링크 전용 경로가 있어 이 스토어가 서버로 보내지 않는다',
    async (type) => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
      global.fetch = fetchMock as unknown as typeof fetch;

      useEvidenceStore.getState().append(makeEvent({ type }));

      // 로컬 반영은 즉시 일어난다(제외 대상이라도 UI 표시는 그대로).
      expect(useEvidenceStore.getState().events).toHaveLength(1);
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  // 코드리뷰 회귀(PR #20 P1): 특권 타입은 서버가 422로 거부하므로(services/evidence.py
  // PRIVILEGED_EVIDENCE_TYPES), 실패가 뻔한 POST 자체를 시도하지 않는다.
  it.each([
    'approval_requested',
    'approval_decided',
    'approval_rejected',
    'approval_escalated',
    'role_granted',
    'role_changed',
    'member_invited',
    'member_removed',
    'delegation_granted',
    'delegation_revoked',
    'dispatch_executed',
    'delivery_confirmed',
  ] as const)('%s는 특권 타입이라 서버로 보내지 않는다(로컬 상태는 그대로 반영)', async (type) => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    global.fetch = fetchMock as unknown as typeof fetch;

    useEvidenceStore.getState().append(makeEvent({ type }));

    expect(useEvidenceStore.getState().events).toHaveLength(1);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('서버 기록이 실패해도 로컬 이벤트는 유지되고 예외가 밖으로 새지 않는다', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch;

    expect(() => useEvidenceStore.getState().append(makeEvent())).not.toThrow();
    await waitFor(() => expect(consoleError).toHaveBeenCalled());
    expect(useEvidenceStore.getState().events).toHaveLength(1);
  });

  it('hydrate는 real 모드에서도 서버로 재전송하지 않는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    global.fetch = fetchMock as unknown as typeof fetch;

    useEvidenceStore.getState().hydrate([makeEvent()]);

    expect(useEvidenceStore.getState().events).toHaveLength(1);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
