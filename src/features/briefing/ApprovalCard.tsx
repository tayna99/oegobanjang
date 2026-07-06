import { Badge } from '@/components/Badge';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { IconSpark } from '@/components/icons';
import { useNextAction } from '@/lib/actionNav';
import { dDayLabel, dDayTone } from '@/lib/dday';
import { severityTone } from '@/lib/badgeTone';
import type { CaseCard } from '@/types';

export interface ApprovalCardProps {
  data: CaseCard;
  layout: 'hero' | 'compact';
  recommendReason?: string;
  onOpen: () => void;
}

// 1단계 스펙 §M1 ApprovalCard — 배지 렌더 순서 고정: [D-day] [누락 N건] [승인 필요] [severity].
// hero만 그림자(카드 자체가 interactive=true로 tap 애니메이션 겸용), compact는 hairline 보더
// (Card의 variant prop이 이미 그 두 시각을 표현한다 — 탭별기획 §1.2).
export function ApprovalCard({ data, layout, recommendReason, onOpen }: ApprovalCardProps) {
  const handleAction = useNextAction();

  return (
    <Card
      variant={layout === 'hero' ? 'hero' : 'default'}
      interactive
      onClick={onOpen}
      className="mb-3 cursor-pointer"
    >
      <h3 className="mb-2 pr-2 text-base font-semibold leading-snug">{data.title}</h3>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {/* DDayTone('critical'|'warning'|'info'|'neutral')은 BadgeTone의 부분집합이라 구조적으로 그대로 대입 가능 — 변환 불필요. */}
        {data.dDay !== undefined && <Badge tone={dDayTone(data.dDay)}>{dDayLabel(data.dDay)}</Badge>}
        {data.missingDocCount !== undefined && data.missingDocCount > 0 && (
          <Badge tone="critical">누락 {data.missingDocCount}건</Badge>
        )}
        {data.approvalRequired && <Badge tone="pending">승인 필요</Badge>}
        <Badge tone={severityTone(data.severity)}>{data.severity}</Badge>
      </div>

      {data.preparedBy === 'agent' && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
          }}
          className="mb-3.5 flex w-full items-center gap-2 rounded-in bg-surface px-3 py-2.5 text-left text-sm font-medium"
        >
          <span className="flex size-[22px] shrink-0 items-center justify-center rounded-lg border border-hairline bg-canvas text-primary">
            <IconSpark width={11} height={11} />
          </span>
          <span>AI가 준비를 마쳤습니다</span>
          {data.preparedRunRef && <span className="ml-auto shrink-0 text-sm font-semibold text-primary">런 {data.preparedRunRef} 보기 →</span>}
        </button>
      )}

      {layout === 'hero' && recommendReason && <p className="mb-1 text-sm text-muted">{recommendReason}</p>}

      <div className="mt-4 flex gap-2.5">
        <Button
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            handleAction(data.caseId, data.secondaryAction);
          }}
          className="flex-1"
        >
          {data.secondaryAction.label}
        </Button>
        <Button
          variant="primary"
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
