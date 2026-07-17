import { fetchMe, logout as apiLogout, requestOtp as apiRequestOtp, verifyOtp as apiVerifyOtp } from '@/lib/api/auth';
import { useRoleStore } from '@/stores/roleStore';
import { useSessionStore } from '@/stores/sessionStore';
import type { Role } from '@/types';

// 실 인증 오케스트레이션(R2.2, NEXT_ROADMAP 2.2) — lib/approval.ts·lib/onboarding.ts와 동일한
// 분리 원칙: lib/api/auth.ts가 순수 fetch를, 이 훅이 스토어 반영(세션+역할)을 담당한다.
function toFrontendRole(role: string): Role | null {
  // expert는 계정이 아니라 패키지 링크 접근이라(7단계 §1) roleStore에 들어오면 안 된다 —
  // 백엔드 membership.role CHECK 제약상 이론적으로 가능해도 여기서 걸러낸다.
  return role === 'owner' || role === 'manager' || role === 'viewer' ? role : null;
}

export interface AuthActions {
  requestOtp: (phone: string) => Promise<{ debugCode: string | null }>;
  /** OTP 검증 → 세션 확립 → 활성 소속 조회 → roleStore에 실제 역할 반영까지 한 번에 처리한다.
   * "역할 파생 절충안": 세션에 role이 있으면 반영하되, 기존 toggleRole() 데모 순환은 그대로
   * 둔다(실서버엔 viewer 데모 계정이 없고, 기존 데모 시연·테스트가 그 토글에 의존한다). */
  verifyAndLogin: (phone: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuthActions(): AuthActions {
  const setSession = useSessionStore((s) => s.setSession);
  const clearSession = useSessionStore((s) => s.clear);
  const setRole = useRoleStore((s) => s.setRole);

  return {
    requestOtp: async (phone) => {
      const result = await apiRequestOtp(phone);
      return { debugCode: result.debugCode };
    },

    verifyAndLogin: async (phone, code) => {
      const verified = await apiVerifyOtp(phone, code);
      // 토큰을 먼저 반영해야 다음 fetchMe() 호출이 인증된 요청으로 나간다
      // (lib/api/client.ts의 apiFetch가 sessionStore.getState().token을 읽는다).
      setSession({ token: verified.token, user: verified.user, membership: null });
      const me = await fetchMe();
      setSession({ token: verified.token, user: verified.user, membership: me.membership, delegatedBy: me.delegatedBy });
      const role = me.membership ? toFrontendRole(me.membership.role) : null;
      if (role) setRole(role);
    },

    logout: async () => {
      await apiLogout();
      clearSession();
    },
  };
}
