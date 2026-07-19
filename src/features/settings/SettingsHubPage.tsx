// 설정 허브 — system-derived (no design source, 7단계 §6 "설정" 행 텍스트만 존재,
// 화면 자체는 없음). CaseWorkbench 행 관용구(이름+부제+›) + CASE_FILTERS 세그먼트
// 버튼 관용구를 그대로 재사용해 조립한다(블루프린트 §9.1-A와 동일 방식) — 새 시각
// 결정 없음. 근거: reference/design-system/design-briefs/README.md(태깅).
import { BackHeader } from '@/components/BackHeader';
import { RoleBlockedNotice } from '@/components/RoleBlockedNotice';
import { cn } from '@/lib/cn';
import { useNav } from '@/lib/nav';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';
import type { ApprovalPolicy } from '@/types';

const POLICY_LABEL: Record<ApprovalPolicy, string> = {
  owner_only: '대표만 승인',
  manager_allowed: '담당자도 승인 가능',
};

function SettingsRow({ label, sublabel, onClick }: { label: string; sublabel: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2.5 border-b border-hairline px-3.5 py-3 text-left last:border-none active:bg-surface"
    >
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-label1 font-semibold text-ink">{label}</span>
        <span className="truncate text-caption1 text-subtle">{sublabel}</span>
      </span>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="shrink-0 text-faint" aria-hidden="true">
        <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

export function SettingsHubPage() {
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const members = useCompanyStore((s) => s.members);
  const delegation = useCompanyStore((s) => s.delegation);
  const approvalPolicy = useCompanyStore((s) => s.approvalPolicy);
  const setApprovalPolicy = useCompanyStore((s) => s.setApprovalPolicy);
  const briefingTime = useCompanyStore((s) => s.briefingTime);
  const setBriefingTime = useCompanyStore((s) => s.setBriefingTime);
  const notificationPrefs = useCompanyStore((s) => s.notificationPrefs);

  // 7단계 §6 "설정: viewer –" — 열람자는 설정에 진입할 수 없다.
  if (role === 'viewer') {
    return (
      <div className="flex min-h-dvh flex-col bg-canvas">
        <BackHeader title="설정" onBack={() => nav.toHome()} />
        <RoleBlockedNotice
          title="열람자 권한으로는 설정에 진입할 수 없습니다."
          subtitle="설정 변경은 대표·담당자만 가능합니다."
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="설정" onBack={() => nav.toHome()} />

      <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">구성원·위임</h3>
          <div className="overflow-hidden rounded-in border border-hairline">
            <SettingsRow
              label="구성원 관리"
              sublabel={`${members.length}명 · ${role === 'owner' ? '초대·역할 변경·제거' : '초대만 가능'}`}
              onClick={() => nav.toSettingsMembers()}
            />
            {/* 위임 관리는 owner 전용(7단계 §6 "설정: owner=위임관리·구성원, manager=초대만") */}
            {role === 'owner' && (
              <SettingsRow
                label="위임 관리"
                sublabel={delegation.active ? '위임 활성' : '위임 없음'}
                onClick={() => nav.toSettingsDelegation()}
              />
            )}
          </div>
        </section>

        {/* 승인 정책은 owner만 변경 가능 — 별도 화면 없이 세그먼트 버튼 1행(§9.1-A 재사용). */}
        {role === 'owner' && (
          <section className="flex flex-col gap-2">
            <h3 className="text-caption1 font-bold text-subtle">승인 정책</h3>
            <div className="flex gap-1.5" role="group" aria-label="승인 정책 선택">
              {(Object.keys(POLICY_LABEL) as ApprovalPolicy[]).map((policy) => {
                const active = policy === approvalPolicy;
                return (
                  <button
                    key={policy}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setApprovalPolicy(policy)}
                    className={cn(
                      'flex-1 rounded-badge px-3 py-2 text-label1 transition-colors duration-btn ease-v2',
                      active
                        ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus'
                        : 'font-medium text-muted shadow-outline hover:bg-surface',
                    )}
                  >
                    {POLICY_LABEL[policy]}
                  </button>
                );
              })}
            </div>
            <p className="text-caption1 text-dim">
              대표만 승인 정책에서는 담당자가 직접 승인하려면 대리 승인 체크가 필요합니다.
            </p>
          </section>
        )}

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">브리핑 시각</h3>
          <div className="flex items-center gap-2.5 rounded-in border border-hairline px-3.5 py-3">
            <input
              type="time"
              value={briefingTime}
              onChange={(event) => setBriefingTime(event.target.value)}
              aria-label="브리핑 시각"
              className="rounded-in bg-canvas px-2 py-1 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
            <span className="text-caption1 text-dim">매일 이 시각에 오늘 브리핑이 생성됩니다</span>
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">알림</h3>
          <div className="overflow-hidden rounded-in border border-hairline">
            <SettingsRow
              label="알림"
              sublabel={`브리핑 ${briefingTime} · 응답 즉시 알림 ${notificationPrefs.responseImmediate ? 'ON' : 'OFF'}`}
              onClick={() => nav.toSettingsNotifications()}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
