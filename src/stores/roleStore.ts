import { create } from 'zustand';
import type { Role } from '@/types';

const DEFAULT_ROLE: Role = 'manager';

interface RoleStoreState {
  role: Role;
  setRole: (role: Role) => void;
  toggleRole: () => void;
  reset: () => void;
}

// 역할 소스 — 로그인/SSO 이전 데모 스위치(4.2, 운영급 확장). 세션 한정(비영속, 새로고침 시
// 담당자로 복귀). visibleCardsForRole(lib/briefing.ts)이 이미 owner/manager/viewer 분기
// 로직을 갖고 있었고, 이 스토어가 그 함수가 기다리던 "role 소스"를 공급한다.
const ROLE_CYCLE: Record<Role, Role> = { manager: 'owner', owner: 'viewer', viewer: 'manager' };

export const useRoleStore = create<RoleStoreState>((set) => ({
  role: DEFAULT_ROLE,
  setRole: (role) => set({ role }),
  toggleRole: () => set((s) => ({ role: ROLE_CYCLE[s.role] })),
  reset: () => set({ role: DEFAULT_ROLE }),
}));
