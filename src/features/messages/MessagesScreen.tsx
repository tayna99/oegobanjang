import { Button } from '@/components/Button';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Skeleton } from '@/components/Skeleton';
import type { MessageThread } from '@/types';
import { ThreadListItem } from './ThreadListItem';

// 탭별기획 §3.1~§3.4 "상태 5종" — BriefingScreen.tsx의 ViewState 유니온 패턴을 그대로 따른다.
// default/empty는 MessagesPage(컨테이너)가 threadStore에서 계산해 넘긴다. loading/error/offline은
// 여기서 완성돼 테스트로 검증되지만, 실제 트리거는 백엔드 접속점 이후(범위 밖).
export type MessagesViewState =
  | { status: 'default'; threads: MessageThread[] }
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'offline'; cachedThreads: MessageThread[]; lastSyncedAt: string };

export interface MessagesScreenProps {
  state: MessagesViewState;
  onOpenThread: (thread: MessageThread) => void;
  onStartFromCases: () => void;
  onRetry?: () => void;
}

// 하단 고정 캡션 — 스펙 문장 그대로, 창작·의역 금지.
const SEND_CAPTION = '모든 메시지는 승인 후에만 발송됩니다';

function ThreadList({
  threads,
  onOpenThread,
  interactive,
}: {
  threads: MessageThread[];
  onOpenThread: (thread: MessageThread) => void;
  interactive?: boolean;
}) {
  return (
    <div>
      {threads.map((thread) => (
        <ThreadListItem
          key={thread.threadId}
          thread={thread}
          onOpen={() => onOpenThread(thread)}
          interactive={interactive}
        />
      ))}
    </div>
  );
}

export function MessagesScreen({ state, onOpenThread, onStartFromCases, onRetry }: MessagesScreenProps) {
  return (
    <main className="mx-auto flex w-full max-w-screen-sm flex-col px-4 pb-24 pt-5">
      {state.status === 'offline' && <OfflineBanner lastSyncedAt={state.lastSyncedAt} />}

      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold text-ink">메시지</h1>
        {state.status === 'default' && (
          <span className="text-sm text-muted">컨택 {state.threads.length}건</span>
        )}
      </header>

      {state.status === 'loading' && (
        <div className="mt-4 space-y-3" aria-hidden="true">
          {/* 임의 bracket 값(h-[72px]) 대신 표준 스케일 사용 — GOTCHAS §4 "Tailwind 임의값 금지"
              (BriefingScreen 스켈레톤과 동일하게 정확한 실제 행 높이 대신 근접한 표준값으로 근사). */}
          <Skeleton className="h-20 rounded-card" />
          <Skeleton className="h-20 rounded-card" />
          <Skeleton className="h-20 rounded-card" />
        </div>
      )}

      {state.status === 'default' && (
        <>
          <ThreadList threads={state.threads} onOpenThread={onOpenThread} />
          <p className="mt-4 text-center text-safety text-faint">{SEND_CAPTION}</p>
        </>
      )}

      {state.status === 'empty' && (
        <div className="mt-4 rounded-card border border-hairline bg-canvas p-5 text-center">
          <p className="text-sm text-muted">아직 컨택 이력이 없습니다</p>
          <Button variant="primary" className="mt-3" onClick={onStartFromCases}>
            케이스에서 시작하기
          </Button>
        </div>
      )}

      {state.status === 'error' && (
        <div className="mt-4">
          <p className="text-sm text-critical-text">메시지를 불러오지 못했습니다</p>
          <Button variant="outline" className="mt-3" onClick={onRetry}>
            다시 시도
          </Button>
        </div>
      )}

      {state.status === 'offline' && (
        <>
          <ThreadList threads={state.cachedThreads} onOpenThread={onOpenThread} interactive={false} />
          <p className="mt-4 text-center text-safety text-faint">{SEND_CAPTION}</p>
        </>
      )}
    </main>
  );
}
