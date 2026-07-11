import { Chip } from '@/components/Chip';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { IconSpark } from '@/components/icons';
import { useNextAction } from '@/lib/actionNav';
import { useNav } from '@/lib/nav';
import { dDayLabel, dDayTone } from '@/lib/dday';
import { severityTone } from '@/lib/chipTone';
import type { CaseCard } from '@/types';

export interface ApprovalCardProps {
  data: CaseCard;
  layout: 'hero' | 'compact';
  recommendReason?: string;
  onOpen: () => void;
  offlineDisabled?: boolean;
}

export function ApprovalCard({ data, layout, recommendReason, onOpen, offlineDisabled }: ApprovalCardProps) {
  const handleAction = useNextAction();
  const nav = useNav();

  return (
    <Card
      variant={layout === 'hero' ? 'hero' : 'default'}
      interactive
      onClick={onOpen}
      data-case-id={data.caseId}
      className="mb-3 cursor-pointer"
    >
      <h3 className="mb-0.5 pr-2 text-body1 font-semibold leading-snug">{data.title}</h3>
      {/* 근로자 부제 — Mobile §2a 카드 서브라인 "Nguyen Van A · 제조1팀" (2.5.4b, title은 업무 단위로 분리) */}
      {data.workerRef && (
        <p className="mb-2 text-label1 text-subtle">
          {data.workerRef.displayName} · {data.workerRef.team}
        </p>
      )}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {data.dDay !== undefined && <Chip tone={dDayTone(data.dDay)}>{dDayLabel(data.dDay)}</Chip>}
        {data.missingDocCount !== undefined && data.missingDocCount > 0 && (
          <Chip tone="critical">누락 {data.missingDocCount}건</Chip>
        )}
        {data.state === 'human_approved' ? (
          <Chip tone="positive">승인 완료</Chip>
        ) : (
          data.approvalRequired && <Chip tone="approval">승인 필요</Chip>
        )}
        <Chip tone={severityTone(data.severity)}>{data.severity}</Chip>
      </div>

      {data.preparedBy === 'agent' && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (data.preparedRunRef) nav.toRun(data.preparedRunRef.replace('#', ''));
          }}
          className="mb-3.5 flex w-full items-center gap-2 rounded-in bg-surface px-3 py-2.5 text-left text-label1 font-medium"
        >
          <span className="flex size-[22px] shrink-0 items-center justify-center rounded-lg border border-hairline bg-canvas text-primary">
            <IconSpark width={11} height={11} />
          </span>
          <span>AI가 준비를 마쳤습니다</span>
          {data.preparedRunRef && <span className="ml-auto shrink-0 text-label1 font-semibold text-primary">런 {data.preparedRunRef} 보기 →</span>}
        </button>
      )}

      {layout === 'hero' && recommendReason && <p className="mb-1 text-body2 text-muted">{recommendReason}</p>}

      <div className="mt-4 flex gap-2.5">
        <Button
          variant="outline"
          disabled={offlineDisabled && data.secondaryAction.requiresApproval}
          onClick={(e) => {
            e.stopPropagation();
            handleAction(data.caseId, data.secondaryAction);
          }}
          className="flex-1"
        >
          {data.secondaryAction.label}
        </Button>
        <Button
          variant={layout === 'hero' ? 'primary' : 'secondary'}
          disabled={offlineDisabled && data.primaryAction.requiresApproval}
          onClick={(e) => {
            e.stopPropagation();
            handleAction(data.caseId, data.primaryAction);
          }}
          className="flex-1"
        >
          {data.primaryAction.label}
        </Button>
      </div>
    </Card>
  );
}
