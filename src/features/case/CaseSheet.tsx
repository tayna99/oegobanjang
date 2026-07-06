import { BottomSheet } from '@/components/BottomSheet';
import { Button } from '@/components/Button';
import { useNextAction } from '@/lib/actionNav';
import type { CaseSheet as CaseSheetData } from '@/mocks/fixtures';
import type { CaseCard } from '@/types';

export interface CaseSheetProps {
  card: CaseCard;
  sheet: CaseSheetData;
  open: boolean;
  onClose: () => void;
}

// 1단계 스펙 §M2 케이스 바텀시트 — 5블록 고정(CaseSummary/AIChecked/MissingDoc/Citation/AgentActivity)
// + ActionBar. 케이스 종류별로 이 컴포넌트를 복제하지 않는다(GOTCHAS §4) — CaseCard·CaseSheetData만으로 구동.
export function CaseSheet({ card, sheet, open, onClose }: CaseSheetProps) {
  const handleAction = useNextAction();
  // GOTCHAS §2 "근거 품질 게이트": citation 0건이면 승인 버튼을 locked로 강등.
  const citationLocked = sheet.citations.length === 0;

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      footer={
        <div className="flex gap-2.5">
          <Button
            variant="outline"
            onClick={() => handleAction(card.caseId, card.secondaryAction)}
            className="flex-1"
          >
            {card.secondaryAction.label}
          </Button>
          <Button
            variant="primary"
            disabled={citationLocked && card.primaryAction.requiresApproval}
            onClick={() => handleAction(card.caseId, card.primaryAction)}
            className="flex-1"
          >
            {card.primaryAction.label}
          </Button>
        </div>
      }
    >
      {/* 1. CaseSummaryBlock */}
      <h3 className="mb-2 mt-1 text-base font-semibold leading-snug">{card.title}</h3>
      <p className="mb-5 text-sm leading-relaxed">{sheet.summary}</p>
      {sheet.guardNote && (
        <div className="mb-5 rounded-in bg-pendbg px-3.5 py-3 text-sm leading-relaxed text-pending">
          {sheet.guardNote}
        </div>
      )}
      {sheet.readinessPercent !== undefined && (
        <div className="mb-5">
          <div className="mb-2 text-xs font-semibold text-muted">준비도 {sheet.readinessPercent}%</div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface">
            <div className="h-full rounded-full bg-primary" style={{ width: `${sheet.readinessPercent}%` }} />
          </div>
        </div>
      )}

      {/* 2. AICheckedBlock */}
      <div className="mb-5">
        <div className="mb-2 text-xs font-semibold text-muted">AI가 확인한 내용</div>
        {sheet.checkedItems.map(({ label, value }) => (
          <div key={label} className="flex justify-between border-b border-surface py-2.5 text-sm last:border-none">
            <span className="text-muted">{label}</span>
            <span className="font-semibold tabular-nums">{value}</span>
          </div>
        ))}
      </div>

      {/* 3. MissingDocChecklist */}
      {sheet.docs && sheet.docs.length > 0 && (
        <div className="mb-5">
          <div className="mb-2 text-xs font-semibold text-muted">서류 · 체크리스트</div>
          {sheet.docs.map(({ name, statusLabel }) => (
            <div key={name} className="flex items-center gap-2.5 border-b border-surface py-2.5 text-sm last:border-none">
              <span>{name}</span>
              <span className="ml-auto text-xs font-semibold text-muted">{statusLabel}</span>
            </div>
          ))}
        </div>
      )}

      {/* 4. CitationBlock */}
      <div className="mb-5">
        <div className="mb-2 text-xs font-semibold text-muted">근거</div>
        {citationLocked ? (
          <div className="rounded-in bg-pendbg px-3.5 py-3 text-sm leading-relaxed text-pending">
            공식 근거가 연결되지 않았습니다. 승인 전 확인이 필요합니다.
          </div>
        ) : (
          sheet.citations.map((c) => (
            <div key={c.title} className="mb-2 rounded-chip bg-surface px-3.5 py-3 text-sm leading-relaxed">
              <span className="mr-1.5 inline-flex size-[18px] items-center justify-center rounded border border-hairline bg-canvas text-xs font-bold text-primary">
                {c.grade}
              </span>
              {c.title}
              <span className="block text-xs text-muted">
                {c.source} · {c.updatedAt}
              </span>
            </div>
          ))
        )}
      </div>

      {/* 5. AgentActivityBlock */}
      {(sheet.activity.length > 0 || sheet.nextWake) && (
        <div className="mb-5">
          <div className="mb-2 text-xs font-semibold text-muted">이 케이스의 에이전트 활동</div>
          {sheet.activity.length > 0 &&
            sheet.activity.map((a) => (
              <div key={a.label} className="flex gap-2.5 py-2 text-sm">
                <span className="min-w-16 shrink-0 text-xs text-muted tabular-nums">{a.at}</span>
                <span>
                  <b className="block font-semibold">{a.label}</b>
                  <span className="text-xs text-muted">{a.detail}</span>
                </span>
              </div>
            ))}
          {sheet.nextWake && <div className="mt-1.5 rounded-in bg-surface px-3 py-2.5 text-xs text-muted">{sheet.nextWake}</div>}
        </div>
      )}
    </BottomSheet>
  );
}
