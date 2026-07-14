import { useParams } from 'react-router-dom';
import { Chip } from '@/components/Chip';
import type { ChipTone } from '@/lib/chipTone';
import { useNav } from '@/lib/nav';
import { expertAccountFor, packagesForExpert } from '@/mocks/expert';
import { ExpertBrandHeader } from './ExpertBrandHeader';

// 행정사 개인 대시보드(7-1, 화이트라벨) — Shell 바깥 최상위 라우트. 영속 매직링크 토큰
// (mock: URL의 expertId)로 진입해, 자기에게 온 여러 회사의 검토 대기 패키지를 회사별로
// 묶어 보여준다. 스펙 §1 "expert가 여러 회사를 보는 뷰"의 실체. 인증은 mock —
// 실서비스는 서명 토큰 + 이메일 OTP(설계 문서 §인증 참고).

function severityTone(label: string): ChipTone {
  if (label.includes('CRITICAL')) return 'critical';
  if (label.includes('HIGH')) return 'high';
  if (label.includes('MEDIUM')) return 'medium';
  return 'neutral';
}

export function ExpertDashboardPage() {
  const { expertId } = useParams<{ expertId: string }>();
  const nav = useNav();
  const account = expertAccountFor(expertId);

  if (!account || !expertId) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">링크를 찾을 수 없습니다.</p>
      </div>
    );
  }

  const groups = packagesForExpert(expertId);
  const total = groups.reduce((sum, group) => sum + group.packages.length, 0);

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col gap-5 bg-canvas px-5 py-8">
      <ExpertBrandHeader account={account} subtitle="검토 요청 대시보드" />

      <div className="flex flex-col gap-1">
        <h1 className="text-heading2 font-bold text-ink">검토 대기 {total}건</h1>
        <p className="text-caption1 text-subtle">연결된 회사 {groups.length}곳 · 계정 없이 안전 링크로 접근합니다</p>
      </div>

      {groups.length === 0 ? (
        <p className="rounded-in bg-surface px-4 py-5 text-center text-body2 text-muted">
          아직 검토 요청이 없습니다.
        </p>
      ) : (
        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <section key={group.tenant.id} aria-label={`${group.tenant.name} 검토 요청`} className="flex flex-col gap-2">
              <div className="flex items-baseline justify-between">
                <h2 className="text-label1 font-bold text-ink">{group.tenant.name}</h2>
                <span className="text-caption1 text-subtle">{group.packages.length}건</span>
              </div>
              <ul className="overflow-hidden rounded-in border border-hairline">
                {group.packages.map((pkg) => (
                  <li key={pkg.packageId}>
                    <button
                      type="button"
                      aria-label={`${pkg.workerName} 검토`}
                      onClick={() => nav.toExpertPackage(expertId, pkg.packageId)}
                      className="flex w-full items-center gap-3 border-b border-hairline px-4 py-3.5 text-left transition-colors duration-btn ease-v2 last:border-none hover:bg-surface"
                    >
                      <div className="flex min-w-0 flex-1 flex-col gap-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Chip tone={severityTone(pkg.severityLabel)}>{pkg.severityLabel}</Chip>
                          <span className="text-caption1 text-subtle">{pkg.workerName}</span>
                        </div>
                        <span className="truncate text-label1 font-semibold text-ink">{pkg.eyebrow}</span>
                      </div>
                      <span aria-hidden="true" className="shrink-0 text-label1 font-semibold text-muted">검토 ›</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <p className="mt-auto pt-2 text-center text-caption1 text-faint">
        열람·회신 이력이 기록됩니다 · 만료형 보안 접근
      </p>
    </div>
  );
}
