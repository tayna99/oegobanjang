import { Chip } from '@/components/Chip';
import { useNav } from '@/lib/nav';
import { THREAD_LIST } from '@/mocks/messages';

// 메시지 탭 — 스레드 목록(2.2). 목록엔 근로자 원문을 노출하지 않는다(GOTCHAS §3, 탭별기획 §3.2):
// 상태 라벨(listLabel)만 표기하고 원문은 스레드 내부(ThreadPage)에서만 보여준다.
export function MessagesPage() {
  const nav = useNav();
  return (
    <div className="mx-auto flex w-full max-w-screen-sm flex-col gap-4 px-4 pb-24 pt-5">
      <header className="flex flex-col gap-0.5">
        <h1 className="text-heading2 font-bold text-ink">메시지</h1>
        <p className="text-pc-sm text-subtle">근로자와의 대화 · 응답 해석</p>
      </header>

      <ul className="flex flex-col gap-2">
        {THREAD_LIST.map((thread) => (
          <li key={thread.threadId}>
            <button
              type="button"
              aria-label={`${thread.workerName} 대화`}
              onClick={() => nav.toThread(thread.threadId)}
              className="flex w-full items-center gap-3 rounded-in border border-hairline px-3.5 py-3 text-left transition-shadow duration-btn ease-v2 active:bg-surface"
            >
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="flex items-center gap-2">
                  <span className="truncate text-label1 font-semibold text-ink">{thread.workerName}</span>
                  <span className="shrink-0 text-caption1 text-dim">{thread.team} · {thread.channel}</span>
                </span>
                {/* 원문이 아니라 상태 라벨만 — 목록 미리보기 원문 노출 금지 */}
                <span className="truncate text-caption1 text-subtle">{thread.listLabel}</span>
              </span>
              {thread.hasResponse && <Chip tone="approval">응답</Chip>}
              <span aria-hidden="true" className="shrink-0 text-label1 font-semibold text-muted">›</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
