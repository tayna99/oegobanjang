// 알림 설정 — 설정 › 알림(A-3). 2단계_알림카탈로그_딥링크맵_v1.md §6 요구사항 표 반영.
// 브리핑 시각은 companyStore.briefingTime 단일 소스를 설정 허브와 함께 바인딩한다(허브에서
// 이동하지 않고 그대로 둠 — 사용자 결정, 2026-07-17). "승인 요청 즉시 알림"은 저장값이 아니다
// — OFF 불가(강제 ON)라 상태로 표현하지 않는다(NotificationPrefs 타입 주석 참고). 목업 원본은
// 이 행을 대표(owner)에게만 노출했으나, 도메인 모델(APPROVER_ROLES=owner+manager,
// manager_allowed가 기본 정책)과 맞지 않아 owner+manager 둘 다에게 노출한다
// (docs/DESIGN_SYNC_AUDIT_2026-07-17.md §1.2에 디자인 내부 결함으로 기록).
import { BackHeader } from '@/components/BackHeader';
import { IconClock, IconLock } from '@/components/icons';
import { RoleBlockedNotice } from '@/components/RoleBlockedNotice';
import { Toggle } from '@/components/Toggle';
import { useNav } from '@/lib/nav';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';

export function NotificationSettingsPage() {
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const briefingTime = useCompanyStore((s) => s.briefingTime);
  const setBriefingTime = useCompanyStore((s) => s.setBriefingTime);
  const prefs = useCompanyStore((s) => s.notificationPrefs);
  const setNotificationPrefs = useCompanyStore((s) => s.setNotificationPrefs);

  // 설정 허브와 동일 가드 — 딥링크로 이 화면에 직접 진입해도 viewer는 차단(MembersPage 관례).
  if (role === 'viewer') {
    return (
      <div className="flex min-h-dvh flex-col bg-canvas">
        <BackHeader title="알림 설정" onBack={() => nav.toHome()} />
        <RoleBlockedNotice
          title="열람자 권한으로는 알림 설정에 진입할 수 없습니다."
          subtitle="알림 설정 변경은 대표·담당자만 가능합니다."
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="알림 설정" onBack={() => nav.toSettings()} />

      <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">브리핑</h3>
          <div className="rounded-in border border-hairline bg-canvas">
            <label className="flex cursor-pointer items-center justify-between gap-3 px-3.5 py-3">
              <span className="flex flex-col gap-0.5">
                <span className="text-label1 font-semibold text-ink">아침 브리핑 시각</span>
                <span className="text-caption1 text-subtle">회사 단위로 적용됩니다 (개인 설정 아님)</span>
              </span>
              <span className="flex shrink-0 items-center gap-1.5">
                <input
                  type="time"
                  value={briefingTime}
                  onChange={(event) => setBriefingTime(event.target.value)}
                  aria-label="브리핑 시각"
                  className="w-[74px] bg-transparent text-label1 font-semibold text-ink outline-none"
                />
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M9 5l7 7l-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-faint" />
                </svg>
              </span>
            </label>
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">알림</h3>
          <div className="overflow-hidden rounded-in border border-hairline bg-canvas">
            <div className="flex flex-col gap-2 border-b border-hairline px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex flex-col gap-0.5 flex-1">
                  <span className="text-label1 font-semibold text-ink">승인 요청 즉시 알림</span>
                  <span className="text-caption1 text-subtle">승인 권한자에게만 표시됩니다</span>
                </span>
                <Toggle checked locked onChange={() => {}} label="승인 요청 즉시 알림" />
              </div>
              <p className="flex items-start gap-1.5 rounded-in bg-surface px-2.5 py-2 text-caption1 leading-relaxed text-subtle">
                <IconLock width={13} height={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                성급한 승인을 막기 위해 항상 켜져 있으며, 끌 수 없습니다.
              </p>
            </div>

            <div className="flex flex-col gap-2 border-b border-hairline px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex flex-col gap-0.5 flex-1">
                  <span className="text-label1 font-semibold text-ink">응답 도착 즉시 알림</span>
                  <span className="text-caption1 text-subtle">근로자 응답이 오면 바로 알립니다</span>
                </span>
                <Toggle
                  checked={prefs.responseImmediate}
                  onChange={(responseImmediate) => setNotificationPrefs({ ...prefs, responseImmediate })}
                  label="응답 도착 즉시 알림"
                />
              </div>
              {!prefs.responseImmediate && (
                <p className="rounded-in bg-surface px-2.5 py-2 text-caption1 leading-relaxed text-subtle">
                  끄면 즉시 알림 대신 아침 다이제스트로 모아 전달됩니다.
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2 border-b border-hairline px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex flex-col gap-0.5 flex-1">
                  <span className="text-label1 font-semibold text-ink">CRITICAL 야간 알림</span>
                  <span className="text-caption1 text-subtle">심야 시간에도 긴급 항목을 알립니다</span>
                </span>
                <Toggle
                  checked={prefs.criticalNight}
                  onChange={(criticalNight) => setNotificationPrefs({ ...prefs, criticalNight })}
                  label="CRITICAL 야간 알림"
                />
              </div>
              {!prefs.criticalNight && (
                <p className="flex items-start gap-1.5 rounded-in bg-warnbg px-2.5 py-2 text-caption1 leading-relaxed text-warning">
                  <IconClock width={13} height={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                  끄면 긴급 항목 확인이 다음 아침까지 늦어질 수 있습니다.
                </p>
              )}
            </div>

            <div className="flex items-center justify-between gap-3 px-3.5 py-3">
              <span className="flex flex-col gap-0.5 flex-1">
                <span className="text-label1 font-semibold text-ink">주간 요약</span>
                <span className="text-caption1 text-subtle">매주 월요일 지난 주 처리 현황을 보내드립니다</span>
              </span>
              <Toggle
                checked={prefs.weeklyDigest}
                onChange={(weeklyDigest) => setNotificationPrefs({ ...prefs, weeklyDigest })}
                label="주간 요약"
              />
            </div>
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">채널</h3>
          <div className="flex items-center justify-between gap-3 rounded-in border border-hairline bg-canvas px-3.5 py-3">
            <span className="flex flex-col gap-0.5">
              <span className="text-label1 font-semibold text-ink">채널 우선순위</span>
              <span className="text-caption1 text-subtle">푸시 실패 시 알림톡으로 자동 전환됩니다</span>
            </span>
            <span className="shrink-0 rounded-badge bg-surface px-2 py-0.5 text-caption1 font-semibold text-dim">
              읽기 전용
            </span>
          </div>
        </section>
      </main>
    </div>
  );
}
