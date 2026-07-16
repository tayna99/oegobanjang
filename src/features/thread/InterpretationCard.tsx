import { Badge } from '@/components/Badge';
import { Button } from '@/components/Button';
import { IconSpark } from '@/components/icons';
import { useNextAction } from '@/lib/actionNav';
import type { Interpretation } from '@/types';

export interface InterpretationCardProps {
  interpretation: Interpretation;
  onConfirm: (updateIds: string[]) => void;
  confirmDisabled?: boolean;
}

// M6 응답 해석 카드 — 1단계 스펙 §M6 KoreanSummary/StatusUpdateProposal/RecommendedActionCard를
// 하나로 묶는다. surface 카드(파랑 배경 아님) — 파랑은 아래 [상태 반영 확인] 버튼 하나에만 쓴다.
export function InterpretationCard({ interpretation, onConfirm, confirmDisabled }: InterpretationCardProps) {
  const handleAction = useNextAction();

  return (
    <div className="rounded-card bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-muted">
          <span className="flex size-5 shrink-0 items-center justify-center rounded-lg border border-hairline bg-canvas text-primary">
            <IconSpark width={11} height={11} />
          </span>
          AI 해석
        </span>
        {/* isFinal:false — 담당자 확인 전 확정 금지(GLOSSARY.md). 배지 필수(1단계 §M6). */}
        <Badge tone="pending">담당자 확인 필요</Badge>
      </div>

      <p className="mb-3 text-sm leading-relaxed text-ink">{interpretation.summaryKo}</p>
      {interpretation.confidence === 'low' && (
        <p className="mb-3 text-sm text-warning-text">해석이 불확실합니다. 원문을 확인해주세요</p>
      )}

      <div className="border-t border-hairline">
        {interpretation.updates.map((update) => (
          <div
            key={update.updateId}
            className="flex items-baseline justify-between gap-3 border-b border-hairline py-2.5 text-sm"
          >
            <span className="text-muted">{update.field}</span>
            <span className="font-semibold text-ink">
              <span className="font-normal text-faint">{update.from} → </span>
              {update.to}
            </span>
          </div>
        ))}
      </div>

      {interpretation.recommendedActions.length > 0 && (
        <div className="mt-3 space-y-2">
          {interpretation.recommendedActions.map((item) => (
            <button
              key={item.action.actionId}
              type="button"
              onClick={() => handleAction(interpretation.caseId, item.action)}
              className="w-full rounded-in border border-hairline bg-canvas px-3.5 py-3 text-left active:bg-surface-dim"
            >
              <span className="block text-sm font-semibold text-ink">{item.action.label}</span>
              <span className="mt-0.5 block text-xs text-muted">{item.reason}</span>
            </button>
          ))}
        </div>
      )}

      {/* 이 화면에서 유일한 primary 파랑 CTA(화면당 1개 원칙). 터치 타깃은 Button 기본
          h-btn 토큰(50px, RunScreen 승인 버튼과 동일 기준)을 따른다 — 임의 px 금지. */}
      <Button
        variant="primary"
        disabled={confirmDisabled}
        onClick={() => onConfirm(interpretation.updates.map((update) => update.updateId))}
        className="mt-4 w-full"
      >
        상태 반영 확인
      </Button>
    </div>
  );
}
