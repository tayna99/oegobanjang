import { useEffect } from 'react';
import { THREADS } from '@/mocks/threads';
import { useThreadStore } from '@/stores/threadStore';
import { sortThreads } from '@/lib/threads';
import { useNav } from '@/lib/nav';
import type { MessageThread } from '@/types';
import { MessagesScreen } from './MessagesScreen';

// 컨테이너 — 스토어 시딩·조회만. 화면 렌더는 MessagesScreen(프레젠테이션) 몫
// (CaseListPage.tsx/BriefingHomePage.tsx와 동일한 컨테이너/프레젠테이션 분리 패턴).
export function MessagesPage() {
  const nav = useNav();
  const threads = useThreadStore((s) => s.threads);
  const upsert = useThreadStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useThreadStore.getState().threads).length === 0) {
      THREADS.forEach(upsert);
    }
  }, [upsert]);

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
