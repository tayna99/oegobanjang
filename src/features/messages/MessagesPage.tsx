import { useSeedThreads } from '@/lib/dataSeed';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { useThreadStore } from '@/stores/threadStore';
import { sortThreads } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import type { MessageThread } from '@/types';
import { MessagesScreen } from './MessagesScreen';
import { MessagesWorkbench } from './MessagesWorkbench';

// 컨테이너 — 스토어 시딩·조회만. 화면 렌더는 MessagesScreen(모바일 프레젠테이션) 몫
// (CaseListPage.tsx/BriefingHomePage.tsx와 동일한 컨테이너/프레젠테이션 분리 패턴).
// lg+에서는 PC 메시지 워크벤치(4c)로 분기 — 다른 케이스 컨테이너와 동일 관례.
// MessagesWorkbench도 이 파일과 같은 threadStore/mocks/threads.ts를 데이터 소스로 쓴다
// (NEXT_ROADMAP D-1, 2026-07-17 — 이전엔 별도 mock(mocks/messages.ts)을 썼던 독립 데이터
// 소스였으나 폐기 후 통합). 모바일·PC 프레젠테이션(MessagesScreen/MessagesWorkbench)만 분리.
export function MessagesPage() {
  const nav = useNav();
  const isDesktop = useIsDesktop();
  const threads = useThreadStore((s) => s.threads);

  useSeedThreads();

  if (isDesktop) {
    return <MessagesWorkbench />;
  }

  const sorted = sortThreads(Object.values(threads));

  function handleOpenThread(thread: MessageThread) {
    // 승인 대기 초안(아직 미발송)은 M3로 직행 — 탭별기획 §3.3 "별도 스레드 뷰를 거치지 않음(뎁스 절약)"
    if (thread.draftCaseId && thread.messages.length === 0) {
      nav.toDraft(thread.draftCaseId);
      return;
    }
    nav.toThread(thread.threadId);
  }

  return (
    <MessagesScreen
      state={sorted.length > 0 ? { status: 'default', threads: sorted } : { status: 'empty' }}
      onOpenThread={handleOpenThread}
      onStartFromCases={() => nav.toCases()}
    />
  );
}
