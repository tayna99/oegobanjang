import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as authApi from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { useRoleStore } from './roleStore';
import { useSessionStore } from './sessionStore';

vi.mock('@/lib/api/auth');

const mockedRequestOtp = vi.mocked(authApi.requestOtp);
const mockedVerifyOtp = vi.mocked(authApi.verifyOtp);
const mockedFetchMe = vi.mocked(authApi.fetchMe);
const mockedLogout = vi.mocked(authApi.logout);

const USER = { id: 'u1', name: '김담당', phone: '010-0000-0001' };

// verifyOtp의 실제 반환 헬퍼(코드리뷰 이후 memberships가 응답에 포함됨 — 별도 fetchMe 없음).
function verifyResult(overrides: Partial<{ sessionToken: string; memberships: authApi.Membership[] }> = {}) {
  return {
    sessionToken: overrides.sessionToken ?? 'tok-1',
    expiresAt: '2026-08-01T00:00:00Z',
    user: USER,
    memberships: overrides.memberships ?? [{ companyId: 'cmp_greenfood', role: 'owner' }],
  };
}

// 지연 실행 가능한 Promise — 재진입/경합 시나리오를 재현하기 위해 resolve 타이밍을 직접 통제한다.
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('sessionStore (R2.2 — 실서버 세션, API_MODE=real일 때만 쓰인다)', () => {
  beforeEach(() => {
    useSessionStore.getState().reset();
    useRoleStore.getState().reset();
    window.localStorage.clear();
    mockedRequestOtp.mockReset();
    mockedVerifyOtp.mockReset();
    mockedFetchMe.mockReset();
    mockedLogout.mockReset();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it('verifyOtp 성공 시 세션이 서고 roleStore가 멤버십 role로 갱신된다(별도 fetchMe 없이)', async () => {
    mockedVerifyOtp.mockResolvedValue(verifyResult({ sessionToken: 'tok-1' }));

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().token).toBe('tok-1');
    expect(useSessionStore.getState().user).toEqual(USER);
    expect(useRoleStore.getState().role).toBe('owner');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBe('tok-1');
    // 코드리뷰 효율 지적 회귀: verify 응답에 멤버십이 실려 오므로 로그인 흐름에서 fetchMe를
    // 또 부르지 않는다(왕복 1회로 절감).
    expect(mockedFetchMe).not.toHaveBeenCalled();
  });

  it('memberships가 비어 있으면 viewer로 fail-closed 처리한다(manager로 승격시키지 않는다)', async () => {
    mockedVerifyOtp.mockResolvedValue(verifyResult({ sessionToken: 'tok-2', memberships: [] }));

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useRoleStore.getState().role).toBe('viewer');
  });

  it('인식 못 하는 role 값(예: expert)도 viewer로 fail-closed 처리한다', async () => {
    mockedVerifyOtp.mockResolvedValue(
      verifyResult({ sessionToken: 'tok-2b', memberships: [{ companyId: 'cmp_x', role: 'expert' }] }),
    );

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useRoleStore.getState().role).toBe('viewer');
  });

  it('role 값이 Object.prototype의 속성 이름과 같아도 프로토타입 체인을 타지 않는다', async () => {
    mockedVerifyOtp.mockResolvedValue(
      verifyResult({ sessionToken: 'tok-2c', memberships: [{ companyId: 'cmp_x', role: 'toString' }] }),
    );

    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');

    expect(useRoleStore.getState().role).toBe('viewer');
  });

  it('verifyOtp 실패 시 anonymous로 남고 에러 메시지를 남긴다', async () => {
    mockedVerifyOtp.mockRejectedValue(new Error('인증번호가 올바르지 않습니다'));

    await expect(useSessionStore.getState().verifyOtp('010-0000-0001', '000000')).rejects.toThrow();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(useSessionStore.getState().error).toBe('인증번호가 올바르지 않습니다');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBeNull();
  });

  // 코드리뷰 회귀: 겹쳐 들어온 verifyOtp 호출 중 나중에 "시작"한 게 아니라 나중에 "응답"한
  // 쪽이 최종 상태를 결정하면 안 된다 — 먼저 시작해 늦게 실패한 호출이 나중에 시작해 먼저
  // 성공한 로그인을 되돌려선 안 된다.
  it('겹쳐 들어온 verifyOtp 중 먼저 시작한 호출이 나중에 실패해도 이후 성공한 로그인을 되돌리지 않는다', async () => {
    const first = deferred<Awaited<ReturnType<typeof authApi.verifyOtp>>>();
    const second = deferred<Awaited<ReturnType<typeof authApi.verifyOtp>>>();
    mockedVerifyOtp.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

    const callA = useSessionStore.getState().verifyOtp('010-0000-0001', '000000'); // 먼저 시작(틀린 코드)
    const callB = useSessionStore.getState().verifyOtp('010-0000-0001', '123456'); // 나중 시작(맞는 코드)

    // B(맞는 코드)가 먼저 응답 — 로그인 성공.
    second.resolve(verifyResult({ sessionToken: 'tok-B' }));
    await callB;
    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().token).toBe('tok-B');

    // A(틀린 코드)가 뒤늦게 실패로 응답 — 이미 확정된 B의 로그인을 되돌리면 안 된다.
    first.reject(new Error('인증번호가 올바르지 않습니다'));
    await expect(callA).rejects.toThrow();

    expect(useSessionStore.getState().status).toBe('authenticated');
    expect(useSessionStore.getState().token).toBe('tok-B');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBe('tok-B');
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

  it('restore는 서버가 명시적으로 거부(401)한 토큰만 지우고 anonymous로 남긴다', async () => {
    window.localStorage.setItem('oegobanjang-session-token', 'tok-expired');
    mockedFetchMe.mockRejectedValue(new ApiError(401, '세션이 만료됐습니다'));

    await useSessionStore.getState().restore();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBeNull();
  });

  // 코드리뷰 회귀: 네트워크 일시 장애를 세션 만료와 동일하게 취급해 유효한 토큰을
  // 지워버리면 안 된다 — 서버가 "무효"라고 확인해준 게 아니므로 토큰을 그대로 둔다.
  it('restore는 네트워크 오류 등 401이 아닌 실패에서는 저장된 토큰을 지우지 않는다', async () => {
    window.localStorage.setItem('oegobanjang-session-token', 'tok-transient');
    mockedFetchMe.mockRejectedValue(new TypeError('Failed to fetch'));

    await useSessionStore.getState().restore();

    expect(useSessionStore.getState().status).toBe('anonymous');
    expect(window.localStorage.getItem('oegobanjang-session-token')).toBe('tok-transient');
  });

  // 코드리뷰 회귀(PR #15 P1): roleStore 기본값(manager)이 real 모드 인증 전에도 그대로
  // 남아 있어 권한 게이트가 관리자 권한으로 열렸다 — restore()는 토큰 유무·성공/실패와
  // 무관하게 항상 먼저 viewer로 fail-closed해야 한다.
  it('restore는 토큰이 없으면 role을 즉시 viewer로 되돌린다(이전 값이 manager여도)', async () => {
    useRoleStore.getState().setRole('manager');
    await useSessionStore.getState().restore();
    expect(useRoleStore.getState().role).toBe('viewer');
    expect(mockedFetchMe).not.toHaveBeenCalled();
  });

  it('restore가 401로 실패해도 role은 viewer로 남는다(이전 값이 manager였어도 복귀하지 않는다)', async () => {
    useRoleStore.getState().setRole('manager');
    window.localStorage.setItem('oegobanjang-session-token', 'tok-expired-2');
    mockedFetchMe.mockRejectedValue(new ApiError(401, '세션이 만료됐습니다'));

    await useSessionStore.getState().restore();

    expect(useRoleStore.getState().role).toBe('viewer');
  });

  it('restore는 저장된 토큰이 없으면 아무 API도 호출하지 않는다', async () => {
    await useSessionStore.getState().restore();
    expect(mockedFetchMe).not.toHaveBeenCalled();
  });

  it('logout은 세션·roleStore를 초기화하고 백엔드에 폐기를 요청한다', async () => {
    mockedVerifyOtp.mockResolvedValue(verifyResult({ sessionToken: 'tok-3' }));
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
    mockedVerifyOtp.mockResolvedValue(verifyResult({ sessionToken: 'tok-4', memberships: [] }));
    await useSessionStore.getState().verifyOtp('010-0000-0001', '123456');
    mockedLogout.mockRejectedValue(new Error('network error'));

    await expect(useSessionStore.getState().logout()).resolves.toBeUndefined();
    expect(useSessionStore.getState().status).toBe('anonymous');
  });
});
