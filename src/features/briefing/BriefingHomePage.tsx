import { visibleCardsForRole } from '@/lib/briefing';
import { sortCaseList } from '@/lib/cases';
import { useSeedCases, useSeedThreads } from '@/lib/dataSeed';
import { countArrivedResponses } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';
import { useThreadStore } from '@/stores/threadStore';
import { BriefingScreen } from './BriefingScreen';

// 근로자 등록 데이터가 아직 없다(3단계 온보딩 몫) — 디자인 세계관 6인 로스터(2.5.4b).
const CURRENT_WORKER_COUNT = 6;

export function BriefingHomePage() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const role = useRoleStore((s) => s.role);
  const companyName = useCompanyStore((s) => s.profile.name);
  const threads = useThreadStore((s) => s.threads);

  useSeedCases();
  useSeedThreads();

  const visible = sortCaseList(visibleCardsForRole(Object.values(cases), role));
  const arrivedResponseCount = countArrivedResponses(Object.values(threads));

  return (
    <BriefingScreen
      header={{ companyName, date: '7월 10일 (금)', unreadNotifications: 0 }}
      state={
        visible.length > 0
          ? { status: 'default', cards: visible, arrivedResponseCount }
          : CURRENT_WORKER_COUNT > 0
            ? { status: 'empty', hasWorkers: true }
            : { status: 'empty', hasWorkers: false }
      }
      onOpenCase={(caseId) => nav.toCase(caseId)}
      onSeeAllCases={() => (CURRENT_WORKER_COUNT > 0 ? nav.toCases() : nav.toOnboarding())}
      onOpenMessages={() => nav.toMessages()}
      role={role}
    />
  );
}
