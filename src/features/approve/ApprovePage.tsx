import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/Button';
import { SAFETY_NOTICE_TEXT } from '@/components/SafetyNotice';
import { dDayLabel } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { DRAFTS } from '@/mocks/drafts';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { usableCitations } from '@/stores/citationStore';
import { cn } from '@/lib/cn';

// 2c 최종 승인 — reference/design-system/외고반장 Mobile.dc.html §2c(145~186행) 이식(M2.6.3).
// 성급한 승인 방지 게이트가 "스트리밍 완료"에서 "사람 체크리스트 필수 N/N"으로 교체된다
// (블루프린트 §2 개정). citation-0 잠금(GOTCHAS §2)은 그대로 이중 게이트로 유지.
// 배너 제목은 고정 문구 정본(SAFETY_NOTICE_TEXT) — 디자인 원문의 변형(C1)은 교정 채택.

function findDraft(caseId: string) {
  return Object.values(DRAFTS).find((draft) => draft.caseId === caseId);
}

export function ApprovePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const transition = useCaseStore((s) => s.transition);
  const requestApproval = useApprovalStore((s) => s.requestApproval);
  const decide = useApprovalStore((s) => s.decide);
  const appendEvidence = useEvidenceStore((s) => s.append);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;
  const sheet = caseId ? CASE_SHEETS[caseId] : undefined;
  const draft = caseId ? findDraft(caseId) : undefined;

  // 승인 체크리스트(디자인 §2c 4항목) — 라벨은 케이스 데이터로 채우는 고정 템플릿.
  const checklist = useMemo(() => {
    if (!card || !sheet) return [];
    const usable = usableCitations(sheet.citations).length;
    return [
      `위험도·영향 검토 완료 (${card.severity}${card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''})`,
      `누락 서류·연결 근거 확인 (근거 ${usable}건)`,
      '단정형 표현 없음 · 표현 가이드 준수',
      draft ? `${draft.langs.map((v) => v.label).join('/')} 초안 내용 확인` : '요청 내용 확인',
    ];
  }, [card, sheet, draft]);

  const [checked, setChecked] = useState<boolean[]>([]);
  const [reason, setReason] = useState('');
  useEffect(() => setChecked(checklist.map(() => false)), [checklist]);

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

  const checkedCount = checked.filter(Boolean).length;
  const allChecked = checkedCount === checklist.length && checklist.length > 0;
  const citationLocked = usableCitations(sheet.citations).length === 0;
  const actionId = card.primaryAction.actionId;

  const decideAndRecord = (decision: 'approved' | 'rejected') => {
    if (!useApprovalStore.getState().approvals[actionId]) requestApproval(actionId);
    decide(actionId, decision, `${actionId}:checklist:${decision}`, decision === 'rejected' ? reason || undefined : undefined);

    if (decision === 'approved') {
      appendEvidence({
        id: `${card.caseId}-checklist-completed`,
        type: 'checklist_completed',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        summary: `필수 ${checklist.length}항목 확인 · 근거 ${usableCitations(sheet.citations).length}건 연결 확인`,
        actor: '김담당',
      });
      appendEvidence({
        id: `${actionId}-approved`,
        type: 'approval_decided',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        evidenceRef: '#4789',
        summary: '승인 확정 · 발송 실행 가능 상태로 전환',
        actor: '김담당 (본인)',
      });
      if (canTransition(card.state, 'human_approved')) transition(card.caseId, 'human_approved');
      nav.toCaseHistory(card.caseId);
      return;
    }

    appendEvidence({
      id: `${actionId}-rejected`,
      type: 'approval_decided',
      at: new Date().toISOString(),
      caseId: card.caseId,
      actionId,
      summary: reason ? `반려 · 사유 기록됨` : '반려',
      actor: '김담당 (본인)',
    });
    if (canTransition(card.state, 'returned')) transition(card.caseId, 'returned');
    nav.toHome();
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="flex items-center gap-2 border-b border-hairline px-3 py-2.5">
        <button
          type="button"
          aria-label="뒤로"
          onClick={() => nav.toCase(card.caseId)}
          className="flex size-11 items-center justify-center rounded-in text-ink active:bg-surface"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <h1 className="text-body1 font-bold text-ink">최종 승인</h1>
      </header>

      <main className="flex flex-1 flex-col gap-5 px-5 pb-40 pt-4">
        <section className="flex flex-col gap-1 rounded-in bg-warnbg px-3.5 py-3">
          <p className="text-safety font-bold text-warning">{SAFETY_NOTICE_TEXT}</p>
          <p className="text-caption1 leading-relaxed text-medium">
            승인 완료 시 발송 실행이 가능해지며, 승인자는 판단 기록에 남습니다.
          </p>
        </section>

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
            {checklist.map((label, index) => (
              <li key={label} className="border-b border-hairline last:border-none">
                <label className="flex min-h-12 cursor-pointer items-center gap-2.5 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={checked[index] ?? false}
                    onChange={() =>
                      setChecked((current) => current.map((value, i) => (i === index ? !value : value)))
                    }
                    className="size-4 accent-[--color-primary-normal]"
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
          disabled={!allChecked || citationLocked}
          onClick={() => decideAndRecord('approved')}
        >
          승인하기
        </Button>
        <Button variant="outline" size="sm" className="w-full" onClick={() => decideAndRecord('rejected')}>
          반려하기
        </Button>
        <p className="text-center text-caption1 text-dim">반려 시 사유가 판단 기록에 남고 요청이 되돌아갑니다.</p>
      </footer>
    </div>
  );
}
