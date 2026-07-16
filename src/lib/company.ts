import { ACTOR_NAME } from '@/lib/approval';
import { ROLE_LABEL } from '@/lib/role';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import type { Role } from '@/types';

// 구성원/위임 생애주기의 단일 출처(lib/approval.ts와 동일한 분리 원칙) —
// 설정 화면(MembersPage/DelegationPage)이 이 유닛을 호출해 스토어 갱신과
// evidence 기록을 함께 오케스트레이션한다. 버튼 가시성에 의한 역할 게이트는
// 화면(UI) 쪽 책임 — CaseWorkbench/ApprovePage와 동일한 관례.
export interface CompanyActions {
  inviteMember: (name: string, role: Role) => void;
  removeMember: (memberId: string) => void;
  changeMemberRole: (memberId: string, role: Role) => void;
  grantDelegation: (delegateId: string, from: string, until?: string) => void;
  revokeDelegation: () => void;
}

export function useCompanyActions(): CompanyActions {
  const members = useCompanyStore((s) => s.members);
  const setMembers = useCompanyStore((s) => s.setMembers);
  const delegation = useCompanyStore((s) => s.delegation);
  const setDelegation = useCompanyStore((s) => s.setDelegation);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const role = useRoleStore((s) => s.role);
  const actorName = `${ROLE_LABEL[role]} ${ACTOR_NAME[role]}`;

  return {
    inviteMember: (name, memberRole) => {
      const id = `member-${Date.now()}`;
      setMembers([...members, { id, name, role: memberRole }]);
      appendEvidence({
        id: `${id}-invited`,
        type: 'member_invited',
        at: new Date().toISOString(),
        summary: `${name}(${ROLE_LABEL[memberRole]}) 초대`,
        actor: actorName,
      });
      appendEvidence({
        id: `${id}-role-granted`,
        type: 'role_granted',
        at: new Date().toISOString(),
        summary: `${name}에게 ${ROLE_LABEL[memberRole]} 역할 부여`,
        actor: actorName,
      });
    },

    removeMember: (memberId) => {
      const member = members.find((m) => m.id === memberId);
      setMembers(members.filter((m) => m.id !== memberId));
      appendEvidence({
        id: `${memberId}-removed-${Date.now()}`,
        type: 'member_removed',
        at: new Date().toISOString(),
        summary: member ? `${member.name} 구성원 제거` : '구성원 제거',
        actor: actorName,
      });
    },

    changeMemberRole: (memberId, newRole) => {
      const member = members.find((m) => m.id === memberId);
      setMembers(members.map((m) => (m.id === memberId ? { ...m, role: newRole } : m)));
      appendEvidence({
        id: `${memberId}-role-changed-${Date.now()}`,
        type: 'role_changed',
        at: new Date().toISOString(),
        summary: member ? `${member.name} 역할을 ${ROLE_LABEL[newRole]}(으)로 변경` : '역할 변경',
        actor: actorName,
      });
    },

    grantDelegation: (delegateId, from, until) => {
      setDelegation({ active: true, ownerId: delegation.ownerId, delegateId, from, until });
      const delegate = members.find((m) => m.id === delegateId);
      appendEvidence({
        id: `delegation-granted-${Date.now()}`,
        type: 'delegation_granted',
        at: new Date().toISOString(),
        summary: delegate ? `${delegate.name}에게 승인 위임 설정` : '승인 위임 설정',
        actor: actorName,
      });
    },

    revokeDelegation: () => {
      setDelegation({ ...delegation, active: false });
      appendEvidence({
        id: `delegation-revoked-${Date.now()}`,
        type: 'delegation_revoked',
        at: new Date().toISOString(),
        summary: '승인 위임 해제',
        actor: actorName,
      });
    },
  };
}
