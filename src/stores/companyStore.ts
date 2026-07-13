import { create } from 'zustand';
import type { ApprovalPolicy, CompanyMember, DelegationConfig } from '@/types';
import { COMPANY_MEMBERS } from '@/mocks/members';

const DEFAULT_DELEGATION: DelegationConfig = {
  active: false,
  ownerId: 'owner-kim',
  delegateId: 'manager-kim',
  from: '2026-07-01',
};
const DEFAULT_POLICY: ApprovalPolicy = 'owner_only'; // 7단계 §2 각주1 — 20인 미만 기본값
const DEFAULT_BRIEFING_TIME = '08:00';

interface CompanyStoreState {
  members: CompanyMember[];
  delegation: DelegationConfig;
  approvalPolicy: ApprovalPolicy;
  briefingTime: string;
  setMembers: (members: CompanyMember[]) => void;
  setDelegation: (delegation: DelegationConfig) => void;
  setApprovalPolicy: (policy: ApprovalPolicy) => void;
  setBriefingTime: (time: string) => void;
  reset: () => void;
}

// 회사(tenant) 설정 — 7단계 권한모델의 순수 상태만 담는다. evidence 기록은 이 스토어의
// 책임이 아니다(lib/approval.ts가 승인/거절 evidence를 별도로 남기는 것과 동일한 분리 —
// lib/company.ts의 useCompanyActions가 이 스토어 갱신 + evidence 기록을 함께 오케스트레이션한다).
export const useCompanyStore = create<CompanyStoreState>((set) => ({
  members: COMPANY_MEMBERS,
  delegation: DEFAULT_DELEGATION,
  approvalPolicy: DEFAULT_POLICY,
  briefingTime: DEFAULT_BRIEFING_TIME,
  setMembers: (members) => set({ members }),
  setDelegation: (delegation) => set({ delegation }),
  setApprovalPolicy: (approvalPolicy) => set({ approvalPolicy }),
  setBriefingTime: (briefingTime) => set({ briefingTime }),
  reset: () =>
    set({
      members: COMPANY_MEMBERS,
      delegation: DEFAULT_DELEGATION,
      approvalPolicy: DEFAULT_POLICY,
      briefingTime: DEFAULT_BRIEFING_TIME,
    }),
}));
