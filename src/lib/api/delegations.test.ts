import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchMyDelegation } from './delegations';

// R2.4 — lib/api/delegations.ts는 순수 fetch+DTO 변환만 한다.
describe('lib/api/delegations', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('위임이 있으면 camelCase로 변환해 반환한다', async () => {
    const dto = { delegation_id: 'dlg1', delegator_user_id: 'usr_owner', delegator_name: '김대표', ends_at: '2027-01-01T00:00:00Z' };
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

    const result = await fetchMyDelegation();

    expect(result).toEqual({ delegatorUserId: 'usr_owner', delegatorName: '김대표', endsAt: '2027-01-01T00:00:00Z' });
  });

  it('위임이 없으면 null을 반환한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('null', { status: 200 })) as unknown as typeof fetch;

    const result = await fetchMyDelegation();

    expect(result).toBeNull();
  });
});
