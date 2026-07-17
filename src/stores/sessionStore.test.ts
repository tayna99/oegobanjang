import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as authApi from '@/lib/api/auth';
import { useRoleStore } from './roleStore';
import { useSessionStore } from './sessionStore';

vi.mock('@/lib/api/auth');

const mockedRequestOtp = vi.mocked(authApi.requestOtp);
const mockedVerifyOtp = vi.mocked(authApi.verifyOtp);
const mockedFetchMe = vi.mocked(authApi.fetchMe);
const mockedLogout = vi.mocked(authApi.logout);

const USER = { id: 'u1', name: '김담당', phone: '010-0000-0001' };

describe('sessionStore (R2.2 — 실서버 세션, API_MODE=real일 때만 쓰인다)', () => {
  beforeEach(() => {
    useSessionStore.getState().reset();
    useRoleStore.getState().reset();
    window.localStorage.clear();
    vi.mocked(authApi.requestOtp).mockReset();
    vi.mocked(authApi.verifyOtp).mockReset();
    vi.mocked(authApi.fetchMe).mockReset();
    vi.mocked(authApi.logout).mockReset();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it('verifyOtp 성공 시 세션이 서고 roleStore가 멤버십 role로 갱신된다', async () => {
    mockedVerifyOtp.mockResolvedValue({ sessionToken: 'tok-1', expiresAt: '2026-08-01T00:00:00Z', user: USER });
    mockedFetchMe.mockResolvedValue({ user: USER, memberships: [{ companyId: 'cmp_greenfood', role: 'owner' }] });

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().token).toBe('tok-1');
    expect(useSessionStore.getState().user).toEqual(USER);
    expect(useRoleStore.getState().role).toBe('owner');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBe('tok-1');
  });

  it('memberships가 비어 있으면 manager로 기본값 처리한다', async () => {
    mockedVerifyOtp.mockResolvedValue({ sessionToken: 'tok-2', expiresAt: '2026-08-01T00:00:00Z', user: USER });
    mockedFetchMe.mockResolvedValue({ user: USER, memberships: [] });

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useRoleStore.getState().role).toBe('manager');
  });

  it('verifyOtp 실패 시 anonymous로 남고 에러 메시지를 남긴다', async () => {
    mockedVerifyOtp.mockRejectedValue(new Error('인증번호가 올바르지 않습니다'));

    await expect(useSessionStore.getState().verifyOtp('010-0000-0001', '000000')).rejects.toThrow();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(useSessionStore.getState().error).toBe('인증번호가 올바르지 않습니다');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBeNull();
  });

  it('requestOtp는 debugCode를 그대로 돌려준다(로컬 환경 힌트)', async () => {
    mockedRequestOtp.mockResolvedValue({ requested: true, expiresInSeconds: 300, debugCode: '654321' });

    const result = await useSessionStore.getState().requestOtp('010-0000-0001');

    expect(result).toEqual({ debugCode: '654321' });
  });

  it('restore는 저장된 토큰이 유효하면 세션을 복원한다(새로고침 대응)', async () => {
    window.localStorage.setItem('oegobanjang-session-token', 'tok-saved');
    mockedFetchMe.mockResolvedValue({ user: USER, memberships: [{ companyId: 'cmp_greenfood', role: 'manager' }] });

    await useSessionStore.getState().restore();

    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().token).toBe('tok-saved');
    expect(useRoleStore.getState().role).toBe('manager');
  });

  it('restore는 저장된 토큰이 만료·무효면 조용히 anonymous로 남긴다', async () => {
    window.localStorage.setItem('oegobanjang-session-token', 'tok-expired');
    mockedFetchMe.mockRejectedValue(new Error('세션이 만료됐습니다'));

    await useSessionStore.getState().restore();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBeNull();
  });

  it('restore는 저장된 토큰이 없으면 아무 API도 호출하지 않는다', async () => {
    await useSessionStore.getState().restore();
    expect(mockedFetchMe).not.toHaveBeenCalled();
  });

  it('logout은 세션·roleStore를 초기화하고 백엔드에 폐기를 요청한다', async () => {
    mockedVerifyOtp.mockResolvedValue({ sessionToken: 'tok-3', expiresAt: '2026-08-01T00:00:00Z', user: USER });
    mockedFetchMe.mockResolvedValue({ user: USER, memberships: [{ companyId: 'cmp_greenfood', role: 'owner' }] });
    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');
    mockedLogout.mockResolvedValue(undefined);

    await useSessionStore.getState().logout();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(useSessionStore.getState().token).toBeNull();
    expect(useRoleStore.getState().role).toBe('manager'); // roleStore 기본값
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBeNull();
    expect(mockedLogout).toHaveBeenCalledWith('tok-3');
  });

  it('logout은 백엔드 호출이 실패해도 로컬 세션은 정리한다(로그아웃은 항상 성공해야 한다)', async () => {
    mockedVerifyOtp.mockResolvedValue({ sessionToken: 'tok-4', expiresAt: '2026-08-01T00:00:00Z', user: USER });
    mockedFetchMe.mockResolvedValue({ user: USER, memberships: [] });
    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');
    mockedLogout.mockRejectedValue(new Error('network error'));

    await expect(useSessionStore.getState().logout()).resolves.toBeUndefined();
    expect(useSessionStore.getState().status).toBe('anonymous');
  });
});
