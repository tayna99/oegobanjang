import { useEffect } from 'react';
import { IconDoc, IconMsg, IconWait } from '@/components/icons';
import { greetingText, visibleCardsForRole, sortCards } from '@/lib/briefing';
import { useNav } from '@/lib/nav';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import type { Role } from '@/types';
import { BriefingScreen } from './BriefingScreen';
import type { SummaryStat } from './SummaryStatRow';

// role 소스가 아직 없다(4.2 온보딩·권한 몫) — 지금은 데모 담당자 페르소나로 고정.
const CURRENT_ROLE: Role = 'manager';
// 근로자 등록 데이터가 아직 없다(3단계 온보딩 몫) — 지금은 "근로자 있음"을 기본값으로 둔다.
const CURRENT_WORKER_COUNT = 5;

export function BriefingHomePage() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const visible = sortCards(visibleCardsForRole(Object.values(cases), CURRENT_ROLE));

  const stats: SummaryStat[] = [
    {
      icon: IconDoc,
      label: '서류 보완',
      count: visible.filter((c) => (c.missingDocCount ?? 0) > 0).length,
      unit: '건',
      onClick: () => nav.toCases(),
    },
    {
      icon: IconWait,
      label: '승인 대기',
      count: visible.filter((c) => c.state === 'approval_pending').length,
      unit: '건',
      onClick: () => nav.toCases(),
    },
    {
      icon: IconMsg,
      label: '응답 도착',
      count: 0,
      unit: '건',
      onClick: () => nav.toMessages(),
    },
  ];

  return (
    <BriefingScreen
      header={{ companyName: '화성 1공장', date: '2026.07.06', unreadNotifications: 0 }}
      state={
        visible.length > 0
          ? { status: 'default', cards: visible, stats, greeting: greetingText(CURRENT_ROLE, visible.length) }
          : CURRENT_WORKER_COUNT > 0
            ? { status: 'empty', hasWorkers: true }
            : { status: 'empty', hasWorkers: false }
      }
      onOpenCase={(caseId) => nav.toCase(caseId)}
      onSeeAllCases={() => (CURRENT_WORKER_COUNT > 0 ? nav.toCases() : nav.toOnboardingWorkers())}
    />
  );
}
