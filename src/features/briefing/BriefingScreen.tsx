import { Button } from '@/components/Button';
import { OfflineBanner } from '@/components/OfflineBanner';
import { SafetyNotice } from '@/components/SafetyNotice';
import { Skeleton } from '@/components/Skeleton';
import { recommendReason } from '@/lib/briefing';
import type { CaseCard } from '@/types';
import { ApprovalCard } from './ApprovalCard';
import { BriefingHeader, type BriefingHeaderProps } from './BriefingHeader';
import { CommandBar } from './CommandBar';
import { SummaryStatRow, type SummaryStat } from './SummaryStatRow';

// 1단계 스펙 §M1 "상태 5종" — 이 유니온이 그 다섯 상태의 유일한 진실이다.
// default/empty는 BriefingHomePage(컨테이너)가 지금 실제로 계산해서 넘기고,
// loading/error/offline은 이 컴포넌트에 완성돼 테스트로 검증되지만 실제 트리거는
// 백엔드 접속점 이후(범위 밖 — 계획 문서 참고).
export type BriefingViewState =
  | { status: 'default'; cards: CaseCard[]; stats: SummaryStat[]; greeting: string }
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

function CardList({
  cards,
  onOpenCase,
  offline,
}: {
  cards: CaseCard[];
  onOpenCase: (caseId: string) => void;
  offline?: boolean;
}) {
  const top3 = cards.slice(0, 3);
  return (
    <>
      {top3.map((card, i) => (
        <ApprovalCard
          key={card.caseId}
          data={card}
          layout={i === 0 ? 'hero' : 'compact'}
          recommendReason={i === 0 ? recommendReason(card) : undefined}
          onOpen={() => onOpenCase(card.caseId)}
          offlineDisabled={offline}
        />
      ))}
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
          <Skeleton className="mt-3 h-7 w-2/3" />
          <div className="mt-5 space-y-3">
            <Skeleton className="h-40 rounded-card" />
            <Skeleton className="h-24 rounded-card" />
            <Skeleton className="h-24 rounded-card" />
          </div>
        </>
      )}

      {state.status === 'default' && (
        <>
          <p className="my-2.5 text-xl font-bold leading-snug">{state.greeting}</p>
          <CardList cards={state.cards} onOpenCase={onOpenCase} />
          {state.cards.length > 3 && (
            <button type="button" onClick={onSeeAllCases} className="mb-4 text-sm font-semibold text-primary">
              케이스에서 {state.cards.length - 3}건 더 보기
            </button>
          )}
          {state.stats.length > 0 && <SummaryStatRow stats={state.stats} />}
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
          <p className="text-xl font-bold">오늘 승인할 업무가 없습니다.</p>
          {state.nextScheduledHint && <p className="mt-2 text-sm text-muted">{state.nextScheduledHint}</p>}
          <Button variant="outline" onClick={onSeeAllCases} className="mt-4">
            케이스 전체 보기
          </Button>
        </div>
      )}

      {state.status === 'empty' && !state.hasWorkers && (
        <div className="mt-3">
          <p className="text-xl font-bold">오늘 승인할 업무가 없습니다.</p>
          <p className="mt-2 text-sm text-muted">근로자를 등록하면 매일 브리핑이 시작됩니다</p>
          <Button variant="primary" onClick={onSeeAllCases} className="mt-4">
            근로자 등록
          </Button>
        </div>
      )}

      {state.status === 'error' && (
        <div className="mt-3">
          <p className="text-base font-semibold">브리핑을 불러오지 못했습니다</p>
          <Button variant="outline" onClick={onSeeAllCases} className="mt-3">
            다시 시도
          </Button>
          {state.hasCachedData && (
            <>
              <p className="mt-4 rounded-in bg-pendbg px-3 py-2 text-sm text-pending">어제 데이터입니다</p>
              <div className="mt-3">
                <CardList cards={state.cachedCards} onOpenCase={onOpenCase} offline />
              </div>
            </>
          )}
        </div>
      )}

      {state.status === 'offline' && <CardList cards={state.cachedCards} onOpenCase={onOpenCase} offline />}
    </div>
  );
}
