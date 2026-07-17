import { afterEach, describe, expect, it } from 'vitest';
import { useSessionStore } from './sessionStore';

describe('sessionStore', () => {
  afterEach(() => useSessionStore.getState().clear());

  it('기본값은 로그인 전 상태(토큰·유저·소속 전부 null)다', () => {
    const state = useSessionStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.membership).toBeNull();
    expect(state.delegatedBy).toEqual([]);
  });

  it('setSession에 delegatedBy를 생략하면 빈 배열로 채운다', () => {
    useSessionStore.getState().setSession({
      token: 'tok1',
      user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
      membership: null,
    });
    expect(useSessionStore.getState().delegatedBy).toEqual([]);
  });

  it('setSession으로 delegatedBy를 반영한다', () => {
    useSessionStore.getState().setSession({
      token: 'tok1',
      user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
      membership: null,
      delegatedBy: [{ userId: 'u_owner', name: '김대표' }],
    });
    expect(useSessionStore.getState().delegatedBy).toEqual([{ userId: 'u_owner', name: '김대표' }]);
  });

  it('setSession으로 세션 전체를 반영한다', () => {
    useSessionStore.getState().setSession({
      token: 'tok1',
      user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
      membership: { companyId: 'cmp1', role: 'manager' },
    });
    const state = useSessionStore.getState();
    expect(state.token).toBe('tok1');
    expect(state.user?.name).toBe('김담당');
    expect(state.membership).toEqual({ companyId: 'cmp1', role: 'manager' });
  });

  it('clear로 로그아웃 상태로 되돌린다', () => {
    useSessionStore.getState().setSession({
      token: 'tok1',
      user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
      membership: null,
    });
    useSessionStore.getState().clear();
    expect(useSessionStore.getState().token).toBeNull();
  });
});
