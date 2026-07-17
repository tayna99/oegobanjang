import { create } from 'zustand';
import { fetchMe, logout as logoutRequest, requestOtp, verifyOtp } from '@/lib/api/auth';
import type { Membership, SessionUser } from '@/lib/api/auth';
import { useRoleStore } from './roleStore';
import type { Role } from '@/types';

// R2.2 — 실서버 세션(플래그가 'real'일 때만 쓰인다, lib/api/config.ts). 세션 토큰은 다른
// 스토어와 달리 새로고침에도 살아남아야 한다(자동 재로그인) — themeStore와 동일한 수동
// localStorage 패턴(zustand persist 미들웨어를 새로 들이지 않는다, 기존 관례 유지).
const STORAGE_KEY = 'oegobanjang-session-token';

const MEMBERSHIP_ROLE_TO_ROLE: Record<string, Role> = { manager: 'manager', owner: 'owner', viewer: 'viewer' };

// memberships[0]을 쓴다 — MVP는 단일 회사 데모 세계관이라 여러 회사 소속 사용자의 "현재 회사"
// 선택 UI는 아직 없다(멀티테넌트 전환 시 후속 과제).
function roleFromMemberships(memberships: Membership[]): Role {
  const role = memberships[0]?.role;
  return role && role in MEMBERSHIP_ROLE_TO_ROLE ? MEMBERSHIP_ROLE_TO_ROLE[role] : 'manager';
}

function readStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

function persistToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  if (token) window.localStorage.setItem(STORAGE_KEY, token);
  else window.localStorage.removeItem(STORAGE_KEY);
}

export type SessionStatus = 'anonymous' | 'authenticating' | 'authenticated';

interface SessionStoreState {
  status: SessionStatus;
  token: string | null;
  user: SessionUser | null;
  memberships: Membership[];
  error: string | null;
  /** O1 "인증번호 받기" — 성공 시 로컬 환경이면 debugCode를 돌려준다(실 SMS 미연동, backend와 동일 관례). */
  requestOtp: (phone: string) => Promise<{ debugCode: string | null }>;
  /** O1 6자리 입력 확인 — 성공하면 세션 토큰을 저장하고 roleStore를 이 세션의 멤버십으로 갱신한다. */
  verifyOtp: (phone: string, code: string) => Promise<void>;
  /** 앱 부팅 시 1회 호출 — 저장된 토큰이 아직 유효하면 세션을 복원한다(새로고침 시 manager로
   * 되돌아가던 M-6 문제의 해소 지점). 유효하지 않으면 조용히 anonymous로 남는다. */
  restore: () => Promise<void>;
  logout: () => Promise<void>;
  reset: () => void;
}

const initialState = {
  status: 'anonymous' as SessionStatus,
  token: null as string | null,
  user: null as SessionUser | null,
  memberships: [] as Membership[],
  error: null as string | null,
};

export const useSessionStore = create<SessionStoreState>((set, get) => ({
  ...initialState,

  requestOtp: async (phone) => {
    set({ error: null });
    try {
      const result = await requestOtp(phone);
      return { debugCode: result.debugCode };
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '인증번호 요청에 실패했습니다' });
      throw err;
    }
  },

  verifyOtp: async (phone, code) => {
    set({ status: 'authenticating', error: null });
    try {
      const verified = await verifyOtp(phone, code);
      const me = await fetchMe(verified.sessionToken);
      persistToken(verified.sessionToken);
      set({ status: 'authenticated', token: verified.sessionToken, user: me.user, memberships: me.memberships, error: null });
      useRoleStore.getState().setRole(roleFromMemberships(me.memberships));
    } catch (err) {
      set({ status: 'anonymous', error: err instanceof Error ? err.message : '인증번호가 올바르지 않습니다' });
      throw err;
    }
  },

  restore: async () => {
    const token = readStoredToken();
    if (!token) return;
    try {
      const me = await fetchMe(token);
      set({ status: 'authenticated', token, user: me.user, memberships: me.memberships, error: null });
      useRoleStore.getState().setRole(roleFromMemberships(me.memberships));
    } catch {
      // 만료·폐기된 토큰 — 조용히 anonymous로 남는다(로그인 화면이 다시 뜬다).
      persistToken(null);
      set({ ...initialState });
    }
  },

  logout: async () => {
    const { token } = get();
    persistToken(null);
    set({ ...initialState });
    useRoleStore.getState().reset();
    if (token) await logoutRequest(token).catch(() => undefined);
  },

  reset: () => {
    persistToken(null);
    set({ ...initialState });
  },
}));
