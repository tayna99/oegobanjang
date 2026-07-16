import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { useNextAction } from '@/lib/actionNav';
import { useApprovalActions } from '@/lib/approval';
import { dDayLabel } from '@/lib/dday';
import { severityTone } from '@/lib/chipTone';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { draftForCase } from '@/mocks/drafts';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { usableCitations } from '@/stores/citationStore';
import { useRoleStore } from '@/stores/roleStore';

// 2b 사례 검토 — reference/design-system/외고반장 Mobile.dc.html §2b(97~142행) 이식(M2.6.2).
// M2 바텀시트를 대체하는 전면 페이지: 케이스 헤드 → 왜 확인이 필요한가요 → 누락 서류 →
// 연결 근거 → 초안 미리보기(언어 토글) → "검토 계속". 승인 버튼은 여기 없다 —
// 승인은 2c 체크리스트 페이지에서만("카드에서는 검토만, 승인은 체크리스트 화면에서").

interface CaseRouteState {
  returnTo?: string;
}

export function CaseReviewPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const nav = useNav();
  const handleAction = useNextAction();
  const { reopenForReview } = useApprovalActions();
  const role = useRoleStore((s) => s.role);
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const returnTo = (location.state as CaseRouteState | null)?.returnTo;

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;
  const baseSheet = caseId ? CASE_SHEETS[caseId] : undefined;
  const docUpdates = useCaseStore((s) => (caseId ? s.docUpdates[caseId] : undefined));
  // 해석 확인(caseStore.applyInterpretationUpdates)이 남긴 갱신을 화면 표시용 statusLabel에
  // 오버레이한다. CASE_SHEETS 원본은 건드리지 않는다.
  const sheet = useMemo(() => {
    if (!baseSheet) return undefined;
    if (!docUpdates || !baseSheet.docs) return baseSheet;
    return {
      ...baseSheet,
      docs: baseSheet.docs.map((doc) =>
        docUpdates[doc.name] ? { ...doc, statusLabel: docUpdates[doc.name].to } : doc,
      ),
    };
  }, [baseSheet, docUpdates]);
  const draft = draftForCase(caseId);
  // 기본 언어는 근로자 언어(비한국어) — 디자인 §2b는 VN이 활성 상태로 열린다.
  const [lang, setLang] = useState(() => {
    const workerLangIndex = draft?.langs.findIndex((variant) => variant.lang !== 'ko') ?? -1;
    return workerLangIndex >= 0 ? workerLangIndex : 0;
  });

  // 2d 타임라인의 "검토 시작" 노드 — 페이지 진입을 판단 기록으로 남긴다(중복 방지 가드).
  useEffect(() => {
    if (!card) return;
    const id = `${card.caseId}-review-started`;
    if (useEvidenceStore.getState().events.some((event) => event.id === id)) return;
    appendEvidence({
      id,
      type: 'review_started',
      at: new Date().toISOString(),
      caseId: card.caseId,
      summary: '모바일에서 사례 검토 진입',
      actor: '김담당',
    });
  }, [card, appendEvidence]);

  const missingDocs = useMemo(() => sheet?.docs?.filter((doc) => doc.status !== 'received') ?? [], [sheet]);
  const citations = sheet?.citations ?? [];

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

  const activeVariant = draft?.langs[lang];

  // 고위험(기한 경과 blocked)은 앱 승인 경로가 아니라 행정사 전달 전용(GOTCHAS 고위험 처리 버튼 금지).
  const highRisk = card.state === 'blocked';

  const onContinue = () => {
    // 반려됐던 케이스는 재검토 위해 승인 대기로 되돌린 뒤 승인 화면으로(코드리뷰 A1/B2 크래시 방지).
    if (card.state === 'returned') reopenForReview(card);
    nav.toApprove(card.caseId);
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="사례 검토" onBack={() => (returnTo ? navigate(returnTo) : navigate(-1))} />

      <main className="flex flex-1 flex-col gap-5 px-5 pb-28 pt-4">
        <section className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <Chip tone={severityTone(card.severity)}>
              {card.severity}
              {card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''}
            </Chip>
            <span className="text-caption1 text-dim">
              {card.caseCode}
              {/* 프로액티브 런 재생 링크 — 판단 기록 #을 눌러 /run/:id로(코드리뷰 B5: 링크 복원, 데모 2막) */}
              {card.preparedRunRef && (
                <>
                  {' · '}
                  <button
                    type="button"
                    onClick={() => nav.toRun(card.preparedRunRef!.replace('#', ''))}
                    className="font-semibold text-primary underline"
                  >
                    판단 기록 {card.preparedRunRef}
                  </button>
                </>
              )}
            </span>
          </div>
          <h2 className="text-heading2 font-bold text-ink">{card.title}</h2>
          {card.workerRef && (
            <p className="text-pc-sm text-subtle">
              {card.workerRef.displayName} · {card.workerRef.team}
              {card.stayExpiryDate ? ` · 체류만료 ${card.stayExpiryDate}` : ''}
            </p>
          )}
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">왜 확인이 필요한가요</h3>
          <p className="text-label1 leading-relaxed text-ink">{sheet.summary}</p>
          {sheet.guardNote && (
            <p className="rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
              {sheet.guardNote}
            </p>
          )}
        </section>

        {missingDocs.length > 0 && (
          <section className="flex flex-col gap-2">
            <h3 className="text-caption1 font-bold text-subtle">누락 서류 ({missingDocs.length})</h3>
            <ul className="overflow-hidden rounded-in border border-hairline">
              {missingDocs.map((doc) => (
                <li key={doc.name} className="flex items-center gap-2.5 border-b border-hairline px-3 py-2.5 last:border-none">
                  <span aria-hidden="true" className="size-3.5 rounded shadow-outline-strong" />
                  <span className="flex-1 text-label1 text-ink">{doc.name}</span>
                  <Chip tone={doc.status === 'missing' ? 'critical' : 'neutral'}>{doc.statusLabel}</Chip>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">연결 근거 ({usableCitations(citations).length})</h3>
          {/* 코드리뷰 지적: 0건 게이트가 raw citations.length를 써 헤더 카운트와 어긋났다. */}
          {usableCitations(citations).length === 0 ? (
            <p className="rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
              공식 근거가 연결되지 않았습니다. 승인 전 확인이 필요합니다.
            </p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {citations.map((citation) => (
                <li key={citation.title} className="flex items-center gap-2.5 rounded-in border border-hairline px-3 py-2.5">
                  <span
                    aria-hidden="true"
                    className="flex size-[18px] shrink-0 items-center justify-center rounded bg-approvalbg text-pc-2xs font-bold text-approval"
                  >
                    {citation.grade}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-label1 text-ink">{citation.title}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {draft && activeVariant && (
          <section className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <h3 className="text-caption1 font-bold text-subtle">초안 미리보기</h3>
              <div className="flex gap-1.5">
                {draft.langs.map((variant, index) => (
                  <button
                    key={variant.lang}
                    type="button"
                    aria-pressed={index === lang}
                    onClick={() => setLang(index)}
                    className={
                      index === lang
                        ? 'rounded-badge bg-approvalbg px-2 py-0.5 text-caption1 font-semibold text-approval shadow-rail-focus'
                        : 'rounded-badge px-2 py-0.5 text-caption1 font-medium text-muted shadow-outline'
                    }
                  >
                    {variant.label}
                  </button>
                ))}
              </div>
            </div>
            <p className="whitespace-pre-line rounded-in bg-surface px-3.5 py-3 text-body2 leading-relaxed text-muted">
              {activeVariant.text}
            </p>
          </section>
        )}
      </main>

      <footer className="fixed inset-x-0 bottom-0 border-t border-hairline bg-canvas px-5 py-3">
        {/* M2 ActionBar 역할 분기(7단계 §6) — viewer는 버튼 없음(읽기 전용). */}
        {role === 'viewer' ? (
          <p className="flex h-btn items-center justify-center text-label1 text-faint">
            열람자 권한으로는 검토만 가능합니다
          </p>
        ) : highRisk ? (
          // 고위험: 앱 승인 없이 행정사 전달 준비만(승인 후) — PC §3b 우측 레일과 동일 규칙.
          <span className="flex h-btn items-center justify-center gap-1.5 rounded-in text-label1 font-semibold text-faint shadow-outline">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="5" y="10" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2" />
            </svg>
            행정사 전달 준비 (승인 후)
          </span>
        ) : card.approvalRequired ? (
          <Button variant="primary" className="w-full" onClick={onContinue}>
            검토 계속
          </Button>
        ) : (
          <Button variant="primary" className="w-full" onClick={() => handleAction(card.caseId, card.primaryAction)}>
            {card.primaryAction.label}
          </Button>
        )}
      </footer>
    </div>
  );
}
