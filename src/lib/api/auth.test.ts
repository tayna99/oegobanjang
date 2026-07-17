import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './client';
import { fetchMe, logout, requestOtp, verifyOtp } from './auth';

vi.mock('./client', () => ({ apiFetch: vi.fn() }));

const mockedApiFetch = vi.mocked(apiFetch);

describe('lib/api/auth (R2.2 — backend/app/api/v1/auth.py 어댑터)', () => {
  afterEach(() => {
    mockedApiFetch.mockReset();
  });

  it('requestOtp는 snake_case 응답을 camelCase로 옮긴다', async () => {
    mockedApiFetch.mockResolvedValue({ requested: true, expires_in_seconds: 300, debug_code: '123456' });

    const result = await requestOtp('010-0000-0001');

    expect(mockedApiFetch).toHaveBeenCalledWith('/api/v1/auth/otp/request', {
      method: 'POST',
      body: { phone: '010-0000-0001' },
    });
    expect(result).toEqual({ requested: true, expiresInSeconds: 300, debugCode: '123456' });
  });

  it('verifyOtp는 세션 토큰·만료시각·사용자 정보를 그대로 옮긴다', async () => {
    const user = { id: 'u1', name: '김담당', phone: '010-0000-0001' };
    mockedApiFetch.mockResolvedValue({ session_token: 'tok', expires_at: '2026-08-01T00:00:00Z', user });

    const result = await verifyOtp('010-0000-0001', '123456');

    expect(mockedApiFetch).toHaveBeenCalledWith('/api/v1/auth/otp/verify', {
      method: 'POST',
      body: { phone: '010-0000-0001', code: '123456' },
    });
    expect(result).toEqual({ sessionToken: 'tok', expiresAt: '2026-08-01T00:00:00Z', user });
  });

  it('fetchMe는 memberships의 company_id를 companyId로 옮긴다', async () => {
    mockedApiFetch.mockResolvedValue({
      user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
      memberships: [{ company_id: 'cmp_greenfood', role: 'manager' }],
    });

    const result = await fetchMe('tok');

    expect(mockedApiFetch).toHaveBeenCalledWith('/api/v1/auth/me', { token: 'tok' });
    expect(result.memberships).toEqual([{ companyId: 'cmp_greenfood', role: 'manager' }]);
  });

  it('logout은 토큰을 실어 POST하고 반환값이 없다', async () => {
    mockedApiFetch.mockResolvedValue(undefined);
    await logout('tok');
    expect(mockedApiFetch).toHaveBeenCalledWith('/api/v1/auth/logout', { method: 'POST', token: 'tok' });
  });
});
