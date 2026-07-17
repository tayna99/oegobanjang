import { useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { Button } from '@/components/Button';
import { useNav } from '@/lib/nav';
import { mergedAuditLogAscending } from '@/lib/audit';
import { cn } from '@/lib/cn';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { EvidenceEvent } from '@/types';

// 2d 승인 이력 — reference/design-system/외고반장 Mobile.dc.html §2d(189~221행) 이식(M2.6.4).
// 승인 1건의 생애 타임라인. 노드 색은 탭별기획 §4.2 정본을 따른다(C9 교정):
// 사람 결정(최종 승인)만 primary 채움, 시스템 이벤트는 무채색.
// 반려는 approval_rejected로 별도 표기 — 승인으로 오기록하지 않는다(코드리뷰 A3 교정).

const NODE_LABEL: Partial<Record<EvidenceEvent['type'], string>> = {
  approval_requested: '승인 요청 생성',
  review_started: '검토 시작',
  checklist_completed: '체크리스트 완료',
  approval_decided: '최종 승인',
  approval_rejected: '반려',
};

export function CaseHistoryPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const events = useEvidenceStore((s) => s.events);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;

  const nodes = useMemo(() => {
    // 표시용 병합은 lib/audit.ts 하나로 통일했다(D-4, NEXT_ROADMAP — 이 병합 로직이 audit.ts의
    // isCaseEscalated와 함께 3곳에 중복돼 있었다). 이 타임라인은 생애주기 순(오래된 것
    // 먼저)이 필요해 mergedAuditLog(최신순)를 reverse()하지 않고 오름차순 변형을 바로
    // 쓴다 — reverse()는 안정 정렬이 보존한 동시각 이벤트의 tie 순서까지 뒤집는다(코드리뷰 지적).
    const combined = mergedAuditLogAscending(events);
    const lifecycle = combined
      .filter((event) => event.caseId === caseId && NODE_LABEL[event.type])
      .map((event) => ({
        key: event.id,
        label: NODE_LABEL[event.type] as string,
        actorTime: `${event.actor ?? 'system'}`,
        detail: event.summary ?? '',
        human: event.type === 'approval_decided',
        hash: event.hash,
      }));
    const decided = events.find(
      (event) => event.caseId === caseId && event.type === 'approval_decided',
    );
    if (decided) {
      lifecycle.push({
        key: `${decided.id}-recorded`,
        label: '판단 기록 저장',
        actorTime: 'system',
        detail: `${decided.evidenceRef ?? ''}${decided.hash ? ` · 해시 기록 ${decided.hash}` : ''}`.trim() || '판단 기록 저장',
        human: false,
        hash: decided.hash,
      });
    }
    return lifecycle;
  }, [events, caseId]);

  const decidedRef = events.find((e) => e.caseId === caseId && e.type === 'approval_decided')?.evidenceRef;

  if (!card) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">케이스를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="승인 이력" onBack={() => nav.toHome()} />

      <main className="flex flex-1 flex-col gap-5 px-5 pb-10 pt-4">
        {card.state === 'human_approved' || card.state === 'completed' ? (
          <section className="flex items-center gap-3 rounded-in border border-hairline p-3.5">
            <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center rounded-full bg-success">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="flex min-w-0 flex-col">
              <span className="text-label1 font-bold text-ink">
                승인 완료{decidedRef ? ` · 판단 기록 ${decidedRef}` : ''}
              </span>
              <span className="truncate text-caption1 text-subtle">
                {card.title}
                {card.workerRef ? ` · ${card.workerRef.displayName}` : ''}
              </span>
            </span>
          </section>
        ) : (
          <section className="rounded-in bg-surface px-3.5 py-3 text-body2 text-muted">
            아직 완료된 승인이 없습니다. 아래는 이 케이스의 진행 기록입니다.
          </section>
        )}

        <ol className="flex flex-col">
          {nodes.map((node) => (
            <li key={node.key} className="flex gap-3">
              <span className="flex w-5 shrink-0 flex-col items-center" aria-hidden="true">
                {/* 탭별기획 §4.2 — 사람 결정 노드만 primary 채움, 시스템 노드는 무채색 */}
                <span
                  className={cn(
                    'mt-0.5 size-3.5 rounded-full',
                    node.human ? 'bg-primary' : 'bg-neutbg shadow-outline-strong',
                  )}
                />
                {/* 정적 마지막 노드(발송 실행 mock)가 항상 뒤따르므로 커넥터는 늘 렌더한다 */}
                <span className="w-0.5 flex-1 bg-neutbg" />
              </span>
              <span className="flex flex-col gap-0.5 pb-4">
                <span className={cn('text-label1 font-semibold', node.human ? 'text-primary' : 'text-ink')}>
                  {node.label}
                </span>
                <span className="text-caption1 text-dim">{node.actorTime}</span>
                {node.detail && <span className="text-pc-sm leading-snug text-subtle">{node.detail}</span>}
              </span>
            </li>
          ))}
          <li className="flex gap-3">
            <span className="flex w-5 shrink-0 flex-col items-center" aria-hidden="true">
              <span className="mt-0.5 size-3.5 rounded-full bg-neutbg" />
            </span>
            <span className="flex flex-col gap-0.5">
              <span className="text-label1 font-semibold text-faint">발송 실행 (mock)</span>
              <span className="text-caption1 text-dim">예정 · PC에서</span>
              <span className="text-pc-sm leading-snug text-subtle">실제 전송 없이 audit trail만 기록</span>
            </span>
          </li>
        </ol>

        <p className="mt-auto rounded-in bg-surface px-3.5 py-3 text-center text-safety text-subtle">
          모든 판단·승인은 Evidence Log에 기록됩니다.
        </p>
      </main>
    </div>
  );
}
