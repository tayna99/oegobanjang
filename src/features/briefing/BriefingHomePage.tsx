import { visibleCardsForRole } from '@/lib/briefing';
import { sortCaseList } from '@/lib/cases';
import { useSeedCases, useSeedEvidence, useSeedThreads } from '@/lib/dataSeed';
import { countArrivedResponses } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { unreadNotificationCount, useNotificationStore } from '@/stores/notificationStore';
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
  // mock 모드는 notificationStore가 항상 빈 배열이라(Shell.tsx의 NotificationBell이 real
  // 모드에서만 hydrate) 이 값은 mock 모드에서 기존과 동일하게 0으로 유지된다 — 이 파일의
  // 다른 real-모드 시딩(useSeedCases 등)과 달리 여기서 useSeedNotifications을 또 부르지
  // 않는다: Shell이 항상 먼저 마운트돼 있어 이미 그 훅이 부팅 시 1회 수신함을 채운다.
  const unreadNotifications = useNotificationStore((s) => unreadNotificationCount(s.records));

  useSeedCases();
  useSeedThreads();
  useSeedEvidence();

  const visible = sortCaseList(visibleCardsForRole(Object.values(cases), role));
  const arrivedResponseCount = countArrivedResponses(Object.values(threads));

  return (
    <BriefingScreen
      header={{ companyName, date: '7월 10일 (금)', unreadNotifications }}
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
