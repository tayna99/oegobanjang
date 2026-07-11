import { useEffect } from 'react';
import { visibleCardsForRole, sortCards } from '@/lib/briefing';
import { useNav } from '@/lib/nav';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import type { Role } from '@/types';
import { BriefingScreen } from './BriefingScreen';

// role 소스가 아직 없다(4.2 온보딩·권한 몫) — 지금은 데모 담당자 페르소나로 고정.
const CURRENT_ROLE: Role = 'manager';
// 근로자 등록 데이터가 아직 없다(3단계 온보딩 몫) — 디자인 세계관 6인 로스터(2.5.4b).
const CURRENT_WORKER_COUNT = 6;

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

  return (
    <BriefingScreen
      header={{ companyName: '그린푸드 제조', date: '7월 10일 (금)', unreadNotifications: 0 }}
      state={
        visible.length > 0
          ? { status: 'default', cards: visible }
          : CURRENT_WORKER_COUNT > 0
            ? { status: 'empty', hasWorkers: true }
            : { status: 'empty', hasWorkers: false }
      }
      onOpenCase={(caseId) => nav.toCase(caseId)}
      onSeeAllCases={() => (CURRENT_WORKER_COUNT > 0 ? nav.toCases() : nav.toOnboardingWorkers())}
    />
  );
}
