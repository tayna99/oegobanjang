import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { Button } from '@/components/Button';
import { SAFETY_NOTICE_TEXT } from '@/components/SafetyNotice';
import { useApprovalActions, canApproveCase, isCitationLocked } from '@/lib/approval';
import { dDayLabel } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { draftForCase } from '@/mocks/drafts';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { usableCitations } from '@/stores/citationStore';
import { cn } from '@/lib/cn';

// 2c 최종 승인 — reference/design-system/외고반장 Mobile.dc.html §2c(145~186행) 이식(M2.6.3).
// 성급한 승인 방지 게이트가 "스트리밍 완료"에서 "사람 체크리스트 필수 N/N"으로 교체된다
// (블루프린트 §2 개정). citation-0 잠금(GOTCHAS §2)·상태 전이 합법성이 이중 게이트.
// 승인/반려 결정 자체는 useApprovalActions 공유 유닛이 수행한다(코드리뷰 A/B/F 근본 교정).

export function ApprovePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const { approve, reject } = useApprovalActions();

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;
  const sheet = caseId ? CASE_SHEETS[caseId] : undefined;
  const draft = draftForCase(caseId);

  // 승인 체크리스트(디자인 §2c 4항목) — 라벨은 케이스 데이터로 채우는 고정 템플릿.
  const checklist = useMemo(() => {
    if (!card || !sheet) return [] as string[];
    const usable = usableCitations(sheet.citations).length;
    return [
      `위험도·영향 검토 완료 (${card.severity}${card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''})`,
      `누락 서류·연결 근거 확인 (근거 ${usable}건)`,
      '단정형 표현 없음 · 표현 가이드 준수',
      draft ? `${draft.langs.map((v) => v.label).join('/')} 초안 내용 확인` : '요청 내용 확인',
    ];
  }, [card, sheet, draft]);

  // 체크 상태는 라벨 Set — 인덱스 boolean[]의 위치 결합(리셋 effect 취약성, 코드리뷰 A5/D)을 없앤다.
  const [checkedLabels, setCheckedLabels] = useState<Set<string>>(() => new Set());
  const [reason, setReason] = useState('');

  if (!card || !sheet) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">케이스를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  const checkedCount = checklist.filter((label) => checkedLabels.has(label)).length;
  const allChecked = checkedCount === checklist.length && checklist.length > 0;
  // 고위험(기한 경과 blocked 등)은 승인 대상이 아니다 — 상태 전이 합법성으로 게이트(코드리뷰 A2/B3/F3).
  const approvable = canApproveCase(card, sheet);
  const citationLocked = isCitationLocked(sheet);
  const highRiskBlocked = !canTransition(card.state, 'human_approved');

  const toggle = (label: string) =>
    setCheckedLabels((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });

  const onApprove = () => {
    if (approve({ card, sheet, checklistCount: checklist.length })) nav.toCaseHistory(card.caseId);
  };
  const onReject = () => {
    if (reject({ card, sheet, reason })) nav.toHome();
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="최종 승인" onBack={() => nav.toCase(card.caseId)} />

      <main className="flex flex-1 flex-col gap-5 px-5 pb-40 pt-4">
        <section className="flex flex-col gap-1 rounded-in bg-warnbg px-3.5 py-3">
          <p className="text-safety font-bold text-warning">{SAFETY_NOTICE_TEXT}</p>
          <p className="text-caption1 leading-relaxed text-medium">
            승인 완료 시 발송 실행이 가능해지며, 승인자는 판단 기록에 남습니다.
          </p>
        </section>

        {/* 고위험 케이스 안내 — 앱 승인 불가, 행정사 전달 전용(GOTCHAS 고위험 처리 버튼 금지). */}
        {highRiskBlocked && sheet.guardNote && (
          <section className="flex flex-col gap-1 rounded-in bg-approvalbg px-3.5 py-3">
            <p className="text-label1 font-semibold text-approval">이 케이스는 앱에서 승인할 수 없습니다</p>
            <p className="text-caption1 leading-relaxed text-approval">{sheet.guardNote}</p>
          </section>
        )}

        <section className="flex flex-col gap-1.5">
          <h3 className="text-caption1 font-bold text-subtle">승인 대상</h3>
          <p className="text-label1 font-semibold text-ink">
            {card.title}
            {card.workerRef ? ` · ${card.workerRef.displayName}` : ''}
          </p>
          <p className="text-caption1 text-dim">
            {card.severity}
            {card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''}
            {card.missingDocCount ? ` · 누락 서류 ${card.missingDocCount}건 요청` : ''}
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-caption1 font-bold text-subtle">승인 체크리스트</h3>
            <span className={cn('text-caption1 font-semibold', allChecked ? 'text-success' : 'text-dim')}>
              필수 {checkedCount}/{checklist.length}
            </span>
          </div>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {checklist.map((label) => (
              <li key={label} className="border-b border-hairline last:border-none">
                <label className="flex min-h-12 cursor-pointer items-center gap-2.5 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={checkedLabels.has(label)}
                    onChange={() => toggle(label)}
                    className="size-4 accent-primary"
                  />
                  <span className="text-label1 text-ink">{label}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">
            의견 / 반려 사유 <span className="font-medium text-dim">(선택)</span>
          </h3>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="추가 의견이 있으면 입력하세요."
            aria-label="의견 / 반려 사유"
            className="h-16 rounded-in bg-canvas px-3 py-2.5 text-label1 text-ink shadow-outline outline-none placeholder:text-faint focus:shadow-rail-focus"
          />
        </section>
      </main>

      <footer className="fixed inset-x-0 bottom-0 flex flex-col gap-2 border-t border-hairline bg-canvas px-5 py-3">
        <Button
          variant="primary"
          className="w-full"
          disabled={!allChecked || citationLocked || !approvable}
          onClick={onApprove}
        >
          승인하기
        </Button>
        <Button variant="outline" size="sm" className="w-full" onClick={onReject}>
          반려하기
        </Button>
        <p className="text-center text-caption1 text-dim">반려 시 사유가 판단 기록에 남고 요청이 되돌아갑니다.</p>
      </footer>
    </div>
  );
}
