import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchMe, logout, requestOtp, verifyOtp } from './auth';

// R2.2 — lib/api/auth.ts는 순수 fetch+DTO 변환만 한다(스토어 반영은 lib/auth.ts 몫).
describe('lib/api/auth', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('requestOtp는 snake_case 응답을 camelCase로 변환한다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ requested: true, expires_in_seconds: 300, debug_code: '123456' }), { status: 200 })) as unknown as typeof fetch;

    const result = await requestOtp('010-0000-0001');
    expect(result).toEqual({ requested: true, expiresInSeconds: 300, debugCode: '123456' });
  });

  it('verifyOtp는 session_token을 token으로 변환한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ session_token: 'tok1', expires_at: '2026-08-01T00:00:00Z', user: { id: 'u1', name: '김담당', phone: '010-0000-0001' } }),
        { status: 200 },
      ),
    ) as unknown as typeof fetch;

    const result = await verifyOtp('010-0000-0001', '123456');
    expect(result).toEqual({ token: 'tok1', expiresAt: '2026-08-01T00:00:00Z', user: { id: 'u1', name: '김담당', phone: '010-0000-0001' } });
  });

  it('fetchMe는 membership이 없으면 null을 그대로 전달한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ user: { id: 'u1', name: '김담당', phone: '010-0000-0001' }, membership: null }), { status: 200 }),
    ) as unknown as typeof fetch;

    const result = await fetchMe();
    expect(result.membership).toBeNull();
  });

  it('fetchMe는 membership의 company_id를 companyId로 변환한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ user: { id: 'u1', name: '김담당', phone: '010-0000-0001' }, membership: { company_id: 'cmp1', role: 'manager' } }),
        { status: 200 },
      ),
    ) as unknown as typeof fetch;

    const result = await fetchMe();
    expect(result.membership).toEqual({ companyId: 'cmp1', role: 'manager' });
  });

  it('logout은 204 빈 응답을 정상 처리한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 })) as unknown as typeof fetch;
    await expect(logout()).resolves.toBeUndefined();
  });
});
