// 구성원 관리 — system-derived(설정 허브와 동일 근거). 행 관용구(CaseWorkbench/MessagesPage)
// + Chip(역할 배지는 상태 톤과 섞이지 않게 neutral/line만 사용, 7단계 §5 role_granted/
// role_changed/member_invited/member_removed evidence) + CASE_FILTERS 세그먼트 버튼
// 관용구(역할 선택, <select> 없이 조립)로 구성한다.
import { useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { BackHeader } from '@/components/BackHeader';
import { cn } from '@/lib/cn';
import { useCompanyActions } from '@/lib/company';
import { useNav } from '@/lib/nav';
import { ROLE_LABEL } from '@/lib/role';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';
import type { Role } from '@/types';

const INVITABLE_ROLES: Role[] = ['manager', 'owner', 'viewer'];

export function MembersPage() {
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const members = useCompanyStore((s) => s.members);
  const { inviteMember, removeMember, changeMemberRole } = useCompanyActions();
  const [name, setName] = useState('');
  const [inviteRole, setInviteRole] = useState<Role>('manager');
  const isOwner = role === 'owner';

  const onInvite = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    inviteMember(trimmed, inviteRole);
    setName('');
  };

  // 7단계 §6 "설정: viewer –" — 열람자는 구성원 관리에 진입할 수 없다.
  if (role === 'viewer') {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">열람자 권한으로는 구성원 관리에 진입할 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toSettings()}>
          설정으로 돌아가기
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="구성원 관리" onBack={() => nav.toSettings()} />

      <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">구성원 {members.length}명</h3>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {members.map((member) => (
              <li
                key={member.id}
                className="flex items-center gap-2.5 border-b border-hairline px-3.5 py-3 last:border-none"
              >
                <span className="min-w-0 flex-1 truncate text-label1 text-ink">{member.name}</span>
                {/* 역할 배지 — 상태 Chip(승인 대기 등)과 혼동되지 않게 무채색만 사용. */}
                <Chip tone="line">{ROLE_LABEL[member.role]}</Chip>
                {/* 역할 변경/제거 — owner CU, manager는 초대만(7단계 §2 매트릭스). */}
                {isOwner && (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        const idx = INVITABLE_ROLES.indexOf(member.role);
                        changeMemberRole(member.id, INVITABLE_ROLES[(idx + 1) % INVITABLE_ROLES.length]);
                      }}
                      aria-label={`${member.name} 역할 변경`}
                      className="rounded-badge px-2 py-1 text-caption1 font-medium text-muted shadow-outline hover:bg-surface"
                    >
                      역할 변경
                    </button>
                    <button
                      type="button"
                      onClick={() => removeMember(member.id)}
                      aria-label={`${member.name} 제거`}
                      className="rounded-badge px-2 py-1 text-caption1 font-medium text-critical-text shadow-outline hover:bg-surface"
                    >
                      제거
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">구성원 초대</h3>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="이름"
            aria-label="초대할 구성원 이름"
            className="h-10 rounded-in bg-canvas px-3 text-label1 text-ink shadow-outline outline-none placeholder:text-faint focus:shadow-rail-focus"
          />
          <div className="flex gap-1.5" role="group" aria-label="초대할 역할 선택">
            {INVITABLE_ROLES.map((r) => {
              const active = r === inviteRole;
              return (
                <button
                  key={r}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setInviteRole(r)}
                  className={cn(
                    'flex-1 rounded-badge px-3 py-2 text-label1 transition-colors duration-btn ease-v2',
                    active
                      ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus'
                      : 'font-medium text-muted shadow-outline hover:bg-surface',
                  )}
                >
                  {ROLE_LABEL[r]}
                </button>
              );
            })}
          </div>
          <Button variant="primary" onClick={onInvite} disabled={!name.trim()}>
            초대
          </Button>
        </section>
      </main>
    </div>
  );
}
