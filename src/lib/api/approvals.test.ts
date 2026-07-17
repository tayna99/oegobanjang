import { afterEach, describe, expect, it, vi } from 'vitest';
import { approveApproval, createApprovalRequest, rejectApproval } from './approvals';

// R2.4 — lib/api/approvals.ts는 순수 fetch+DTO 변환만 한다(schemas/approval.py
// ApprovalDecisionRequest/ApprovalDecisionResponse 그대로 매핑).
describe('lib/api/approvals', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  const responseDto = { approval: { id: 'apv1', status: 'approved' }, case_state: 'human_approved' };

  it('approveApproval은 POST /api/v1/approvals/{id}/approve를 호출하고 case_state를 반환한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(responseDto), { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await approveApproval('apv1', {
      idempotencyKey: 'k1',
      identityMethod: 'pin',
      pin: '1234',
      checklist: [{ key: 'risk', label: '위험도 검토', checked: true }],
    });

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/approvals/apv1/approve',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          idempotency_key: 'k1',
          on_behalf_of_user_id: null,
          identity_method: 'pin',
          pin: '1234',
          reason: null,
          checklist: [{ key: 'risk', label: '위험도 검토', checked: true }],
        }),
      }),
    );
    expect(result).toEqual({ caseState: 'human_approved' });
  });

  it('rejectApproval은 POST /api/v1/approvals/{id}/reject를 호출한다', async () => {
    const rejectedDto = { approval: { id: 'apv1', status: 'rejected' }, case_state: 'returned' };
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(rejectedDto), { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await rejectApproval('apv1', {
      idempotencyKey: 'k2',
      identityMethod: 'pin',
      pin: '1234',
      reason: '사유',
    });

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/approvals/apv1/reject',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result).toEqual({ caseState: 'returned' });
  });

  it('createApprovalRequest는 POST /api/v1/approvals를 호출하고 approvalId를 반환한다', async () => {
    const createDto = { approval: { id: 'apv_new', status: 'pending' }, case_state: 'approval_pending' };
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(createDto), { status: 201 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await createApprovalRequest('act1');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/approvals',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ action_id: 'act1' }) }),
    );
    expect(result).toEqual({ approvalId: 'apv_new', caseState: 'approval_pending' });
  });
});
