import { create } from 'zustand';
import { ApiError } from '@/lib/api/client';
import { fetchMe, logout as logoutRequest, requestOtp, verifyOtp } from '@/lib/api/auth';
import type { Membership, SessionUser } from '@/lib/api/auth';
import { useRoleStore } from './roleStore';
import type { Role } from '@/types';

// R2.2 — 실서버 세션(플래그가 'real'일 때만 쓰인다, lib/api/config.ts). 세션 토큰은 다른
// 스토어와 달리 새로고침에도 살아남아야 한다(자동 재로그인) — themeStore와 동일한 수동
// localStorage 패턴(zustand persist 미들웨어를 새로 들이지 않는다, 기존 관례 유지).
const STORAGE_KEY = 'oegobanjang-session-token';

const MEMBERSHIP_ROLE_TO_ROLE: Partial<Record<string, Role>> = { manager: 'manager', owner: 'owner', viewer: 'viewer' };

// memberships[0]을 쓴다 — MVP는 단일 회사 데모 세계관이라 여러 회사 소속 사용자의 "현재 회사"
// 선택 UI는 아직 없다(멀티테넌트 전환 시 후속 과제).
//
// 코드리뷰 지적 2건 반영: (1) `in` 연산자는 프로토타입 체인까지 매칭해 role 문자열이
// 'toString'/'constructor' 같은 값이면 통과해버린다 — `Object.hasOwn`으로 교정. (2) 멤버십이
// 없거나(예: status='removed'만 남은 사용자) 인식 못 할 role(백엔드는 'expert'도 허용하지만
// 프론트 Role엔 없음)이면 가장 큰 권한인 'manager'가 아니라 가장 작은 권한인 'viewer'로
// fail-closed한다.
function roleFromMemberships(memberships: Membership[]): Role {
  const role = memberships[0]?.role;
  if (role && Object.hasOwn(MEMBERSHIP_ROLE_TO_ROLE, role)) {
    return MEMBERSHIP_ROLE_TO_ROLE[role] as Role;
  }
  return 'viewer';
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
  error: null as string | null,
};

// 코드리뷰 지적: verifyOtp/restore에 재진입 가드가 없어, 겹쳐 들어온 두 요청 중 나중에
// "시작"한 쪽이 아니라 나중에 "응답"한 쪽이 최종 상태를 결정했다(오타 수정 후 재입력 등으로
// 실제 재현 가능). 호출마다 순번을 매기고, set() 직전에 "아직 최신 호출인지"를 확인해
// 스테일 응답이 최신 상태를 덮어쓰지 못하게 한다.
let activeRequestId = 0;

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
    const requestId = ++activeRequestId;
    set({ status: 'authenticating', error: null });
    try {
      // 코드리뷰 지적: verify 응답에 이미 memberships가 실려 온다(backend R2 리뷰 반영) —
      // 이전엔 여기서 별도로 fetchMe()를 또 불러 로그인마다 왕복이 2회였고, 그 fetchMe가
      // 네트워크 문제로 실패하면 "코드는 맞았는데 방금 발급된 유효 토큰을 통째로 버리고
      // '인증번호가 올바르지 않습니다'라고 오해시키는" 버그가 있었다 — 별도 호출 자체를
      // 없애 그 실패 모드를 구조적으로 제거한다.
      const verified = await verifyOtp(phone, code);
      // 재진입 가드는 "공유 상태를 건드릴 자격"만 막는다 — 이 호출 자체의 성공/실패는
      // 항상 정직하게 호출자에게 돌려준다(그래야 StepPhoneAuth의 개별 try/catch가 자기
      // 요청의 진짜 결과를 안다). 스테일 성공은 조용히 무시하고 최신 상태를 건드리지 않는다.
      if (requestId === activeRequestId) {
        persistToken(verified.sessionToken);
        set({ status: 'authenticated', token: verified.sessionToken, user: verified.user, error: null });
        useRoleStore.getState().setRole(roleFromMemberships(verified.memberships));
      }
    } catch (err) {
      if (requestId === activeRequestId) {
        set({ status: 'anonymous', error: err instanceof Error ? err.message : '인증번호가 올바르지 않습니다' });
      }
      throw err;
    }
  },

  restore: async () => {
    // 코드리뷰 지적(PR #15 P1): 세션이 없거나 복원이 실패해도 roleStore가 이전 기본값
    // (manager, mock 데모용 초기값)에 그대로 남아 인증 전 UI 권한 게이트가 관리자 권한으로
    // 열렸다 — 복원을 시도하기 전에 먼저 최소 권한(viewer)으로 fail-closed하고, 실제로
    // 유효한 세션이 확인됐을 때만 그 위에 진짜 role을 덮어쓴다. async 함수 본문은 첫
    // await(fetchMe) 전까지 동기 실행되므로, main.tsx가 restore()를 기다리지 않고
    // (`void restore()`) 곧바로 렌더해도 이 setRole은 렌더보다 항상 먼저 끝난다.
    useRoleStore.getState().setRole('viewer');
    const token = readStoredToken();
    if (!token) return;
    const requestId = ++activeRequestId;
    try {
      const me = await fetchMe(token);
      if (requestId !== activeRequestId) return;
      set({ status: 'authenticated', token, user: me.user, error: null });
      useRoleStore.getState().setRole(roleFromMemberships(me.memberships));
    } catch (err) {
      if (requestId !== activeRequestId) return;
      // 코드리뷰 지적: 세션이 "서버가 확인한 무효"(401)인지 "확인 자체가 안 됨"(네트워크
      // 일시 장애·backend 재기동 등)인지 구분하지 않고 전부 토큰을 지워버렸다 — 후자는
      // 아직 유효한 토큰을 영구 삭제해 불필요한 재로그인을 강제한다. 서버가 명시적으로
      // 거부한 경우에만 지운다.
      if (err instanceof ApiError && err.status === 401) {
        persistToken(null);
        set({ ...initialState });
      }
      // 그 외(네트워크 오류 등)에는 토큰을 그대로 두고 anonymous로만 남는다 — 다음 새로고침이나
      // 재시도가 성공하면 정상 로그인된다.
    }
  },

  logout: async () => {
    const { token } = get();
    activeRequestId += 1; // 진행 중이던 verify/restore 응답을 전부 무효화한다.
    persistToken(null);
    set({ ...initialState });
    useRoleStore.getState().reset();
    if (token) await logoutRequest(token).catch(() => undefined);
  },

  reset: () => {
    activeRequestId += 1;
    persistToken(null);
    set({ ...initialState });
  },
}));
