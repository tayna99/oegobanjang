import { formatBriefingDate, visibleCardsForRole } from '@/lib/briefing';
import { sortCaseList } from '@/lib/cases';
import { useSeedBriefing, useSeedCases, useSeedEvidence, useSeedThreads } from '@/lib/dataSeed';
import { countArrivedResponses } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import { useBriefingStore } from '@/stores/briefingStore';
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
  const briefing = useBriefingStore((s) => s.briefing);
  // mock 모드는 notificationStore가 항상 빈 배열이라(Shell.tsx의 NotificationBell이 real
  // 모드에서만 hydrate) 이 값은 mock 모드에서 기존과 동일하게 0으로 유지된다 — 이 파일의
  // 다른 real-모드 시딩(useSeedCases 등)과 달리 여기서 useSeedNotifications을 또 부르지
  // 않는다: Shell이 항상 먼저 마운트돼 있어 이미 그 훅이 부팅 시 1회 수신함을 채운다.
  const unreadNotifications = useNotificationStore((s) => unreadNotificationCount(s.records));

  useSeedCases();
  useSeedThreads();
  useSeedEvidence();
  useSeedBriefing();

  const visible = sortCaseList(visibleCardsForRole(Object.values(cases), role));
  const arrivedResponseCount = countArrivedResponses(Object.values(threads));
  // real 모드에서 서버 브리핑이 도착하면 실제 날짜를 쓰고, 그 전(mock 모드 포함)에는 기존
  // 데모 세계관 문구를 그대로 유지한다(동작 무변경 — DEMO_TODAY와 동일한 고정 문구).
  const dateLabel = briefing ? formatBriefingDate(briefing.briefingDate) : '7월 10일 (금)';

  return (
    <BriefingScreen
      header={{ companyName, date: dateLabel, unreadNotifications }}
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
