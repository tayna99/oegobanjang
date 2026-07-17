import { useMemo } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { useSeedCases } from '@/lib/dataSeed';
import { useNav } from '@/lib/nav';
import { deriveMonthlyReport } from '@/lib/ownerReport';
import { ROLE_LABEL } from '@/lib/role';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// 사장님(owner) PC 최소화면(4f) — reference/design-system/외고반장 PC_4a-4f(신규티어)
// .dc.html §4f(556~625행) 이식. "의도적으로 최소화 — 월간 리포트 열람 + 구성원·위임 설정만 ·
// 승인은 모바일에서"(7단계 §2 각주3의 owner=승인만, 실행 대리 아님 원칙과 일치). 담당자의
// 풍부한 운영 화면(ControlTowerPage)은 owner에게 보여주지 않는다 — HomePage에서 role 분기.
// R1.8부터 처리한 케이스·사전 감지·승인 없는 발송은 스토어 파생값이다(lib/ownerReport.ts).
// 평균 승인 소요만 아직 mock — 이유는 그 파일 주석 참고(D-6, 2.5.6과 동일 판단).
const MOCK_APPROVAL_DURATION = { avgApprovalHours: 1.8, avgApprovalHoursLastMonth: 4.2 };

export function OwnerHomeWorkbench() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const events = useEvidenceStore((s) => s.events);
  const members = useCompanyStore((s) => s.members);
  const delegation = useCompanyStore((s) => s.delegation);

  useSeedCases();

  const pendingCount = Object.values(cases).filter((c) => c.state === 'approval_pending').length;
  const delegate = delegation.active ? members.find((m) => m.id === delegation.delegateId) : undefined;
  const report = useMemo(() => deriveMonthlyReport(Object.values(cases), events), [cases, events]);

  return (
    <section aria-label="사장님 홈" className="mx-auto flex h-[calc(100dvh-4rem)] max-w-screen-md flex-col gap-5 overflow-y-auto p-6">
      {pendingCount > 0 ? (
        <div className="rounded-in bg-approvalbg px-4 py-3">
          <p className="text-label1 font-semibold text-approval">
            승인 대기 {pendingCount}건이 있습니다 — 승인은 모바일 앱에서 처리해 주세요.
          </p>
          <p className="text-caption1 text-approval">이 화면은 열람·설정 전용입니다.</p>
        </div>
      ) : (
        <div className="rounded-in bg-surface px-4 py-3">
          <p className="text-label1 font-semibold text-ink">승인 대기 항목이 없습니다.</p>
        </div>
      )}

      <section className="flex flex-col gap-2.5">
        <h1 className="text-heading2 font-bold text-ink">이번 달 운영 리포트</h1>
        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col gap-1 rounded-card border border-hairline p-3.5">
            <span className="text-pc-2xs text-subtle">처리한 케이스</span>
            <span className="text-heading2 font-bold tabular-nums text-ink">{report.processedCases}건</span>
          </div>
          <div className="flex flex-col gap-1 rounded-card border border-hairline p-3.5">
            <span className="text-pc-2xs text-subtle">사전 감지</span>
            <span className="text-heading2 font-bold tabular-nums text-ink">
              {report.proactiveDetected}건 <span className="text-pc-xs font-semibold text-success">({report.proactivePercent}%)</span>
            </span>
          </div>
          <div className="flex flex-col gap-1 rounded-card border border-hairline p-3.5">
            <span className="text-pc-2xs text-subtle">평균 승인 소요</span>
            <span className="text-heading2 font-bold tabular-nums text-ink">{MOCK_APPROVAL_DURATION.avgApprovalHours}시간</span>
            <span className="text-pc-2xs text-faint">지난달 {MOCK_APPROVAL_DURATION.avgApprovalHoursLastMonth}시간</span>
          </div>
        </div>
        <div className="rounded-in bg-surface px-3.5 py-2.5 text-caption1 text-ink">
          승인 없는 외부 발송 {report.unauthorizedSendCount}건 · 전 기간 동일
        </div>
      </section>

      <section className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <h2 className="text-label1 font-bold text-ink">구성원 · 위임</h2>
          <Button variant="outline" size="sm" onClick={() => nav.toSettingsMembers()}>
            구성원 초대
          </Button>
        </div>
        <ul className="overflow-hidden rounded-in border border-hairline">
          {members.map((member) => (
            <li key={member.id} className="flex items-center gap-2.5 border-b border-hairline px-3.5 py-3 last:border-none">
              <span className="min-w-0 flex-1 truncate text-label1 text-ink">{member.name}</span>
              <Chip tone="line">{ROLE_LABEL[member.role]}</Chip>
              {delegate?.id === member.id && (
                <span className="shrink-0 text-caption1 text-approval">대리 승인 위임 중</span>
              )}
            </li>
          ))}
        </ul>
        <Button variant="outline" size="sm" className="self-start" onClick={() => nav.toSettingsDelegation()}>
          위임 설정
        </Button>
        <p className="text-caption1 text-faint">행정사는 구성원이 아닙니다 — 만료형 링크로만 패키지를 수신합니다.</p>
      </section>
    </section>
  );
}
