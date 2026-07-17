import { afterEach, describe, expect, it, vi } from 'vitest';
import { approveApproval, createApprovalRequest, rejectApproval } from './approvals';
import { ApiError } from './client';

const APPROVAL_DTO = {
  id: 'apv1',
  company_id: 'cmp1',
  case_id: 'cs1',
  action_id: 'act1',
  status: 'approved',
  idempotency_key: 'key1',
  reason: null,
  requested_at: '2026-07-17T00:00:00Z',
  decided_at: '2026-07-17T01:00:00Z',
  decided_by_user_id: 'u1',
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

describe('lib/api/approvals', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('createApprovalRequest는 action_id로 POST /api/v1/approvals를 호출한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse({ approval: APPROVAL_DTO, case_state: 'approval_pending' }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await createApprovalRequest('act1');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/approvals',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ action_id: 'act1' }) }),
    );
    expect(result.approval.id).toBe('apv1');
  });

  it('approveApproval은 approval_id로 /approve를 호출하고 스네이크케이스 바디를 보낸다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse({ approval: APPROVAL_DTO, case_state: 'human_approved' }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await approveApproval('apv1', {
      idempotencyKey: 'key1',
      identityMethod: 'pin',
      pin: '1234',
      onBehalfOfUserId: 'u_owner',
    });

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/api/v1/approvals/apv1/approve');
    expect(JSON.parse(init.body as string)).toEqual({
      idempotency_key: 'key1',
      identity_method: 'pin',
      pin: '1234',
      on_behalf_of_user_id: 'u_owner',
      reason: undefined,
    });
    expect(result.case_state).toBe('human_approved');
  });

  it('rejectApproval은 approval_id로 /reject를 호출한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(jsonResponse({ approval: APPROVAL_DTO, case_state: 'returned' }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await rejectApproval('apv1', { idempotencyKey: 'key1', identityMethod: 'pin', pin: '1234', reason: '근거 부족' });

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/api/v1/approvals/apv1/reject');
    expect(result.case_state).toBe('returned');
  });

  it('비2xx 응답은 ApiError로 던져 호출부가 사용자 가시 에러로 변환할 수 있게 한다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: 'PIN이 일치하지 않습니다' }, 422)) as unknown as typeof fetch;

    const error = await approveApproval('apv1', { idempotencyKey: 'key1', identityMethod: 'pin', pin: '0000' }).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(422);
  });
});
