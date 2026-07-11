import { Button } from '@/components/Button';
import { OfflineBanner } from '@/components/OfflineBanner';
import { SafetyNotice } from '@/components/SafetyNotice';
import { Skeleton } from '@/components/Skeleton';
import type { CaseCard } from '@/types';
import { ApprovalCard } from './ApprovalCard';
import { AgentProgressList } from './AgentProgressList';
import { BriefingHeader, type BriefingHeaderProps } from './BriefingHeader';
import { CommandBar } from './CommandBar';
import { PipelineStatRow } from './PipelineStatRow';

// M1 오늘 브리핑 — M2.6.1에서 디자인 §2a(승인 큐 중심)로 재구성:
// 파이프라인 스탯 로우 → "내가 처리할 승인 N건"(단일 검토 CTA 카드) →
// "에이전트 진행 중 N건" → SafetyNotice → CommandBar(스펙 트랙 존치, 블루프린트 §1).
// 상태 5종 유니온은 유일한 진실 그대로 유지(1단계 §M1).
export type BriefingViewState =
  | { status: 'default'; cards: CaseCard[] }
  | { status: 'empty'; hasWorkers: true; nextScheduledHint?: string }
  | { status: 'empty'; hasWorkers: false }
  | { status: 'loading' }
  | { status: 'error'; hasCachedData: false }
  | { status: 'error'; hasCachedData: true; cachedCards: CaseCard[] }
  | { status: 'offline'; cachedCards: CaseCard[]; lastSyncedAt: string };

export interface BriefingScreenProps {
  state: BriefingViewState;
  header: BriefingHeaderProps;
  onOpenCase: (caseId: string) => void;
  onSeeAllCases: () => void;
}

// 승인 큐 = 내가 결정해야 하는 카드(승인 대기·반려 보완·기한 경과 강제 전달).
function approvalQueue(cards: CaseCard[]): CaseCard[] {
  return cards.filter(
    (card) =>
      card.approvalRequired &&
      (card.state === 'approval_pending' || card.state === 'blocked' || card.state === 'returned'),
  );
}

// 에이전트 진행 중 = 아직 승인 단계에 오지 않은 카드(감지·수집·초안·확인 대기).
function agentProgress(cards: CaseCard[]): CaseCard[] {
  const queue = new Set(approvalQueue(cards).map((card) => card.caseId));
  return cards.filter(
    (card) => !queue.has(card.caseId) && card.state !== 'completed' && card.state !== 'human_approved',
  );
}

function QueueSection({
  cards,
  onOpenCase,
  offline,
}: {
  cards: CaseCard[];
  onOpenCase: (caseId: string) => void;
  offline?: boolean;
}) {
  const queue = approvalQueue(cards);
  const progress = agentProgress(cards);
  return (
    <>
      <PipelineStatRow cards={cards} />
      <section className="mt-4" aria-label="승인 큐">
        <h2 className="mb-2 text-pc-sm font-semibold text-subtle">내가 처리할 승인 {queue.length}건</h2>
        {queue.map((card) => (
          <ApprovalCard
            key={card.caseId}
            data={card}
            onReview={() => onOpenCase(card.caseId)}
            offlineDisabled={offline}
          />
        ))}
      </section>
      {progress.length > 0 && (
        <section className="mt-4" aria-label="에이전트 진행 중">
          <h2 className="mb-2 text-pc-sm font-semibold text-subtle">에이전트 진행 중 {progress.length}건</h2>
          <AgentProgressList cards={progress} onOpenCase={onOpenCase} />
        </section>
      )}
    </>
  );
}

export function BriefingScreen({ state, header, onOpenCase, onSeeAllCases }: BriefingScreenProps) {
  return (
    <div className="p-5">
      {state.status === 'offline' && <OfflineBanner lastSyncedAt={state.lastSyncedAt} />}
      <BriefingHeader {...header} />

      {state.status === 'loading' && (
        <>
          <Skeleton className="mt-3 h-14" />
          <div className="mt-5 space-y-3">
            <Skeleton className="h-24 rounded-card" />
            <Skeleton className="h-24 rounded-card" />
            <Skeleton className="h-24 rounded-card" />
          </div>
        </>
      )}

      {state.status === 'default' && (
        <>
          <QueueSection cards={state.cards} onOpenCase={onOpenCase} />
          <div className="mt-4">
            <SafetyNotice />
          </div>
          <div className="mt-4">
            <CommandBar />
          </div>
        </>
      )}

      {state.status === 'empty' && state.hasWorkers && (
        <div className="mt-3">
          <p className="text-heading1 font-bold">오늘 승인할 업무가 없습니다.</p>
          {state.nextScheduledHint && <p className="mt-2 text-body2 text-muted">{state.nextScheduledHint}</p>}
          <Button variant="outline" onClick={onSeeAllCases} className="mt-4">
            케이스 전체 보기
          </Button>
        </div>
      )}

      {state.status === 'empty' && !state.hasWorkers && (
        <div className="mt-3">
          <p className="text-heading1 font-bold">오늘 승인할 업무가 없습니다.</p>
          <p className="mt-2 text-body2 text-muted">근로자를 등록하면 매일 브리핑이 시작됩니다</p>
          <Button variant="primary" onClick={onSeeAllCases} className="mt-4">
            근로자 등록
          </Button>
        </div>
      )}

      {state.status === 'error' && (
        <div className="mt-3">
          <p className="text-body1 font-semibold">브리핑을 불러오지 못했습니다</p>
          <Button variant="outline" onClick={onSeeAllCases} className="mt-3">
            다시 시도
          </Button>
          {state.hasCachedData && (
            <>
              <p className="mt-4 rounded-in bg-approvalbg px-3 py-2 text-label1 text-approval">어제 데이터입니다</p>
              <div className="mt-3">
                <QueueSection cards={state.cachedCards} onOpenCase={onOpenCase} offline />
              </div>
            </>
          )}
        </div>
      )}

      {state.status === 'offline' && <QueueSection cards={state.cachedCards} onOpenCase={onOpenCase} offline />}
    </div>
  );
}
