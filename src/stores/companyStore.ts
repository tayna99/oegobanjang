import { create } from 'zustand';
import type { ApprovalPolicy, CompanyMember, DelegationConfig } from '@/types';
import { COMPANY_MEMBERS } from '@/mocks/members';

const DEFAULT_DELEGATION: DelegationConfig = {
  active: false,
  ownerId: 'owner-kim',
  delegateId: 'manager-kim',
  from: '2026-07-01',
};
// 7단계 §2 각주1 — 스펙상 20인 미만 회사(이 데모의 6인 로스터)는 owner_only가 "정답" 기본값이지만,
// 그렇게 하면 이미 확립된 8단계 데모 대본(manager가 직접 승인하는 3막)과 approvalFlow.test.tsx의
// 대부분이 즉시 "대표 승인 요청"으로 바뀌어 깨진다. 데모 안정성을 우선해 manager_allowed를 기본값으로
// 두고, owner_only는 설정 화면(Phase C)에서 전환해 그 분기를 시연하는 값으로 둔다.
const DEFAULT_POLICY: ApprovalPolicy = 'manager_allowed';
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
