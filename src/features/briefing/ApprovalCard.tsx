import { Chip } from '@/components/Chip';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { dDayLabel } from '@/lib/dday';
import { severityTone } from '@/lib/chipTone';
import type { CaseCard } from '@/types';

// 승인 큐 카드 — reference/design-system/외고반장 Mobile.dc.html §2a(52~75행) 이식(M2.6.1).
// CTA는 "검토" 1개뿐이다: 카드에서는 검토만, 승인은 체크리스트 화면(2c)에서만
// (GOTCHAS §3 개정 2026-07-11 — 구 2CTA 규칙 대체). preparedRunRef 재생 링크는
// 2b 검토 페이지의 판단 기록 링크로 이동했다(블루프린트 §2 데모 대응).
// 버튼 높이는 디자인 34px 대신 h-btn-sm(44px) — 터치 타깃 44px 규칙(rules/frontend.md)이 우선.

export interface ApprovalCardProps {
  data: CaseCard;
  onReview: () => void;
  offlineDisabled?: boolean;
  /** 열람자(viewer)는 M1 CTA가 비활성(7단계 §6 "읽기 전용(버튼 비활성)"). */
  readOnly?: boolean;
  /** 자동 에스컬레이션(7단계 §3.2) — 48h/72h 미응답으로 재알림·이관이 발생한 케이스. */
  escalated?: boolean;
}

const SEVERITY_LABEL: Record<CaseCard['severity'], string> = {
  CRITICAL: '긴급',
  HIGH: '높음',
  MEDIUM: '중간',
  LOW: '낮음',
};

export function ApprovalCard({ data, onReview, offlineDisabled, readOnly, escalated }: ApprovalCardProps) {
  return (
    <Card data-case-id={data.caseId} className="mb-3 flex items-center gap-3 p-4">
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap gap-1.5">
          <Chip tone={severityTone(data.severity)}>
            {SEVERITY_LABEL[data.severity]}
            {data.dDay !== undefined ? ` · ${dDayLabel(data.dDay)}` : ''}
          </Chip>
          {data.missingDocCount !== undefined && data.missingDocCount > 0 && (
            <Chip tone="critical">누락 {data.missingDocCount}건</Chip>
          )}
          {data.state === 'returned' && <Chip tone="high">반려됨 · 보완 필요</Chip>}
          {escalated && <Chip tone="high">승인 지연</Chip>}
        </div>
        <h3 className="truncate text-label1 font-semibold text-ink">{data.title}</h3>
        {data.workerRef && (
          <p className="truncate text-pc-xs text-subtle">
            {data.workerRef.displayName} · {data.workerRef.team}
          </p>
        )}
      </div>
      <Button variant="primary" size="sm" disabled={offlineDisabled || readOnly} onClick={onReview} className="shrink-0">
        검토
      </Button>
    </Card>
  );
}
