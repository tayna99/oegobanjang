import { useEffect } from 'react';
import { CASE_CARDS } from '@/mocks/fixtures';
import { THREADS } from '@/mocks/threads';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { useThreadStore } from '@/stores/threadStore';
import { fetchCases } from './api/cases';
import { API_MODE } from './api/config';
import { fetchEvidence } from './api/evidence';
import { fetchNotifications } from './api/notifications';
import { fetchThreadDetail, fetchThreads } from './api/threads';

// 13개 화면에 반복되던 "스토어가 비어있으면 픽스처로 시드" useEffect를 한 곳으로 모은다
// (R2.3, NEXT_ROADMAP 2.3 — D-4류 중복 제거와 배선을 동시에 처리). API_MODE가 'mock'이면
// 지금까지와 동일하게 CASE_CARDS/THREADS를 동기 시드한다 — 켜져 있으면 백엔드에서 fetch해
// 채운다. fetch는 비동기라 첫 렌더는 비어있다가 응답이 오면 이 훅을 구독 중인 컴포넌트가
// 자동 재렌더된다(별도 로딩 상태 없이 기존 "empty" 화면이 잠깐 보였다 채워지는 정도 —
// 2.3은 읽기 배선까지만 스코프).
//
// briefings.ts의 fetchLatestBriefing()(브리핑 당일 랭크 서브셋)은 여기서 쓰지 않는다 —
// caseStore는 화면 진입 순서와 무관하게 항상 "전체 케이스"가 채워져 있다는 것을 모든
// 화면이 전제하는 단일 스토어라, 어떤 화면이 먼저 뜨느냐에 따라 서브셋으로 시드돼버리면
// (예: 브리핑 화면이 먼저 떠서 케이스 목록 화면이 빈 스토어로 착각하지 못하는 버그) 다른
// 화면들이 전체 목록을 다시 못 채운다. 브리핑 전용 서브셋을 쓰려면 별도 스토어 슬롯이
// 필요한데, 이는 2.3 스코프 밖 — fetchLatestBriefing()은 만들어 뒀지만 아직 어떤 화면에도
// 배선하지 않는다.
export function useSeedCases(): void {
  const upsert = useCaseStore((s) => s.upsert);
  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length > 0) return;
    if (API_MODE === 'real') {
      // 로그인 전(세션 토큰 없음)에는 401이 정상 — 콘솔에 처리되지 않은 프로미스 거부로
      // 새지 않게만 막는다. 스토어는 비어 있는 채로 남고, 로그인 후 재진입하면 다시 시도된다.
      fetchCases()
        .then((cases) => cases.forEach(upsert))
        .catch((err: unknown) => console.error('[dataSeed] 케이스 조회 실패', err));
    } else {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);
}

export function useSeedThreads(): void {
  const upsert = useThreadStore((s) => s.upsert);
  useEffect(() => {
    if (Object.keys(useThreadStore.getState().threads).length > 0) return;
    if (API_MODE === 'real') {
      fetchThreads()
        .then((threads) => threads.forEach(upsert))
        .catch((err: unknown) => console.error('[dataSeed] 스레드 조회 실패', err));
    } else {
      THREADS.forEach(upsert);
    }
  }, [upsert]);
}

// 목록(useSeedThreads)이 채워 넣는 건 가벼운 요약(threads.ts의 toThreadSummary — 메시지·해석
// 없음)이라, 특정 스레드를 열람하는 화면(ThreadPage/MessagesWorkbench)은 이 훅으로 상세를
// 마저 채워 넣는다. mock 모드는 useSeedThreads()가 이미 완전한 데이터를 넣어두므로 아무 것도
// 하지 않는다(기존 동작 100% 보존).
export function useSeedThreadDetail(threadId: string | undefined): void {
  const upsert = useThreadStore((s) => s.upsert);
  useEffect(() => {
    if (API_MODE !== 'real' || !threadId) return;
    fetchThreadDetail(threadId)
      .then(upsert)
      .catch((err: unknown) => console.error('[dataSeed] 스레드 상세 조회 실패', err));
  }, [threadId, upsert]);
}

// R2.5 — mock 모드는 아무 것도 하지 않는다: 시드(EVIDENCE_SEED)는 evidenceStore에 담기지
// 않고 표시 시점에 lib/audit.ts가 합친다(기존 관례 그대로). real 모드에서만 서버에 이미
// 기록된 이벤트를 부팅 시 1회 hydrate한다(재기록 아님 — evidenceStore.hydrate 참조).
export function useSeedEvidence(): void {
  const hydrate = useEvidenceStore((s) => s.hydrate);
  useEffect(() => {
    if (API_MODE !== 'real') return;
    if (useEvidenceStore.getState().events.length > 0) return;
    fetchEvidence()
      .then(hydrate)
      .catch((err: unknown) => console.error('[dataSeed] 판단 기록 조회 실패', err));
  }, [hydrate]);
}

// R5.4 — mock 모드는 notificationStore를 절대 채우지 않는다(초기값 빈 배열 그대로) — 알림
// 센터·unreadNotifications 배지는 mock 모드에서 항상 "알림 없음"으로 렌더된다(동작 무변경
// 보장, BriefingHomePage의 unreadNotifications:0 배선 참조). real 모드에서만 부팅 시 1회
// 서버 수신함을 hydrate한다 — Shell.tsx의 NotificationBell이 이 훅을 호출해, 앱이 뜨는 동안
// 항상 한 번은 채워진다.
export function useSeedNotifications(): void {
  const hydrate = useNotificationStore((s) => s.hydrate);
  useEffect(() => {
    if (API_MODE !== 'real') return;
    fetchNotifications()
      .then(hydrate)
      .catch((err: unknown) => console.error('[dataSeed] 알림 조회 실패', err));
  }, [hydrate]);
}
