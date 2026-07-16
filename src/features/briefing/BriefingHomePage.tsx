import { useEffect } from 'react';
import { IconDoc, IconMsg, IconWait } from '@/components/icons';
import { greetingText, visibleCardsForRole, sortCards } from '@/lib/briefing';
import { countArrivedResponses } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import { CASE_CARDS } from '@/mocks/fixtures';
import { THREADS } from '@/mocks/threads';
import { useCaseStore } from '@/stores/caseStore';
import { useThreadStore } from '@/stores/threadStore';
import type { Role } from '@/types';
import { BriefingScreen } from './BriefingScreen';
import type { SummaryStat } from './SummaryStatRow';

// role 소스가 아직 없다(4.2 온보딩·권한 몫) — 지금은 데모 담당자 페르소나로 고정.
const CURRENT_ROLE: Role = 'manager';
// 근로자 등록 데이터가 아직 없다(3단계 온보딩 몫) — 디자인 세계관 6인 로스터(2.5.4b).
const CURRENT_WORKER_COUNT = 6;

export function BriefingHomePage() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const threads = useThreadStore((s) => s.threads);
  const upsertThread = useThreadStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  useEffect(() => {
    if (Object.keys(useThreadStore.getState().threads).length === 0) {
      THREADS.forEach(upsertThread);
    }
  }, [upsertThread]);

  const visible = sortCards(visibleCardsForRole(Object.values(cases), CURRENT_ROLE));
  const arrivedResponseCount = countArrivedResponses(Object.values(threads));

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
      count: arrivedResponseCount,
      unit: '건',
      onClick: () => nav.toMessages(),
    },
  ];

  return (
    <BriefingScreen
      header={{ companyName: '그린푸드 제조', date: '2026.07.10', unreadNotifications: 0 }}
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
