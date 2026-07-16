import { useEffect } from 'react';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { THREADS } from '@/mocks/threads';
import { useThreadStore } from '@/stores/threadStore';
import { sortThreads } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import type { MessageThread } from '@/types';
import { MessagesScreen } from './MessagesScreen';
import { MessagesWorkbench } from './MessagesWorkbench';

// 컨테이너 — 스토어 시딩·조회만. 화면 렌더는 MessagesScreen(모바일 프레젠테이션) 몫
// (CaseListPage.tsx/BriefingHomePage.tsx와 동일한 컨테이너/프레젠테이션 분리 패턴).
// lg+에서는 PC 메시지 워크벤치(4c)로 분기 — 다른 케이스 컨테이너와 동일 관례.
// MessagesWorkbench는 별도 mock(mocks/messages.ts)을 쓰는 독립 데이터 소스다 — threadStore로
// 통합하는 것은 후속(두 화면의 데이터 계약을 하나로 합치는 건 별도 리팩터 범위).
export function MessagesPage() {
  const nav = useNav();
  const isDesktop = useIsDesktop();
  const threads = useThreadStore((s) => s.threads);
  const upsert = useThreadStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useThreadStore.getState().threads).length === 0) {
      THREADS.forEach(upsert);
    }
  }, [upsert]);

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
