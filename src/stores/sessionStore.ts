import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SessionUser {
  id: string;
  name: string;
  phone: string;
}

// 백엔드 role 원문(owner/manager/viewer/expert) — 프론트 Role 유니온으로의 매핑은
// 소비처(lib/api/auth.ts)가 담당한다. expert는 계정이 아니라 링크 접근이라(7단계 §1)
// 세션에 나타나면 안 되지만, 백엔드 응답 타입 자체는 이 유니온이 그대로다.
export type MembershipRole = 'owner' | 'manager' | 'viewer' | 'expert';

export interface SessionMembership {
  companyId: string;
  role: MembershipRole;
}

// R2.4 — 로그인 사용자가 대리 승인할 수 있는 owner(들)(§13-10). ApprovePage의 "대리 승인"
// 체크박스가 하드코딩된 OWNER_NAME 대신 이 값을 쓴다.
export interface DelegatedBy {
  userId: string;
  name: string;
}

interface SessionStoreState {
  token: string | null;
  user: SessionUser | null;
  membership: SessionMembership | null;
  delegatedBy: DelegatedBy[];
  setSession: (session: {
    token: string;
    user: SessionUser;
    membership: SessionMembership | null;
    delegatedBy?: DelegatedBy[];
  }) => void;
  clear: () => void;
}

// 실 인증 세션(R2.2, NEXT_ROADMAP 2.2) — localStorage에 영속화한다. 백엔드 세션 토큰이
// 30일 TTL로 설계돼 있어(backend/app/services/auth.py SESSION_TTL), 새로고침마다 재로그인을
// 요구하면 서버 설계와 어긋난다. 실 서비스 전환 시 저장 위치(메모리·httpOnly 쿠키 등)는
// 재검토 대상 — 지금은 파일럿/데모 전제(USE_REAL_API가 꺼져 있으면 이 스토어는 아예 쓰이지
// 않는다).
export const useSessionStore = create<SessionStoreState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      membership: null,
      delegatedBy: [],
      setSession: (session) =>
        set({
          token: session.token,
          user: session.user,
          membership: session.membership,
          delegatedBy: session.delegatedBy ?? [],
        }),
      clear: () => set({ token: null, user: null, membership: null, delegatedBy: [] }),
    }),
    { name: 'ogb-session' },
  ),
);
