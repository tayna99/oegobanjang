import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { Button } from '@/components/Button';
import { BottomSheet } from '@/components/BottomSheet';
import { OfflineBanner } from '@/components/OfflineBanner';
import { SAFETY_NOTICE_TEXT } from '@/components/SafetyNotice';
import { useApprovalActions, canApproveCase, isCitationLocked, OWNER_NAME } from '@/lib/approval';
import { ApiError } from '@/lib/api/client';
import { API_MODE } from '@/lib/api/config';
import { createApprovalRequest, type DecisionChecklistItem } from '@/lib/api/approvals';
import { type CaseDetail, fetchCaseDetail } from '@/lib/api/cases';
import { fetchMyDelegation, type MyDelegation } from '@/lib/api/delegations';
import { mergedAuditLog } from '@/lib/audit';
import { useSeedCases, useSeedEvidence } from '@/lib/dataSeed';
import { dDayLabel } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { DEMO_PIN, isValidPinFormat } from '@/lib/pin';
import { useOnline } from '@/lib/useOnline';
import { CASE_SHEETS } from '@/mocks/fixtures';
import { draftForCase } from '@/mocks/drafts';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { usableCitations } from '@/stores/citationStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import { cn } from '@/lib/cn';

// 2c 최종 승인 — reference/design-system/외고반장 Mobile.dc.html §2c(145~186행) 이식(M2.6.3).
// 성급한 승인 방지 게이트가 "스트리밍 완료"에서 "사람 체크리스트 필수 N/N"으로 교체된다
// (블루프린트 §2 개정). citation-0 잠금(GOTCHAS §2)·상태 전이 합법성이 이중 게이트.
// 승인/반려 결정 자체는 useApprovalActions 공유 유닛이 수행한다(코드리뷰 A/B/F 근본 교정).
//
// R2.4 — real 모드는 체크리스트·근거수·가드노트·승인 id를 mock CASE_SHEETS 대신
// GET /api/v1/cases/{id}(fetchCaseDetail)에서 얻는다. 반려도 이제 PIN 시트를 거친다
// (사용자 결정 — DB 정본이 승인·반려 모두 본인확인을 요구, mock/real UX 통일).

interface ChecklistItem {
  key: string;
  label: string;
}

export function ApprovePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const { approve, reject, requestOwnerApproval } = useApprovalActions();
  const role = useRoleStore((s) => s.role);
  const approvalPolicy = useCompanyStore((s) => s.approvalPolicy);
  const events = useEvidenceStore((s) => s.events);
  const isOnline = useOnline();

  useSeedCases();
  useSeedEvidence();

  const card = caseId ? cases[caseId] : undefined;
  const sheet = caseId ? CASE_SHEETS[caseId] : undefined;
  const draft = draftForCase(caseId);

  // real 모드 전용 서버 상세(Blocker A+B 해소) — mock 모드는 아무 것도 하지 않는다.
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(API_MODE === 'real');
  const [myDelegation, setMyDelegation] = useState<MyDelegation | null>(null);
  const [autoRequestFailed, setAutoRequestFailed] = useState(false);

  useEffect(() => {
    if (API_MODE !== 'real' || !caseId) return;
    let cancelled = false;
    setDetailLoading(true);
    Promise.all([fetchCaseDetail(caseId), fetchMyDelegation()])
      .then(([caseDetail, delegation]) => {
        if (cancelled) return;
        setDetail(caseDetail);
        setMyDelegation(delegation);
      })
      .catch((err: unknown) => {
        if (!cancelled) console.error('[ApprovePage] 케이스 상세 조회 실패', err);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  // pending approval이 없고 manager 세션이며 액션이 요청 가능한 상태면 자동으로 생성한다
  // (mock 모드의 "카드 진입 즉시 승인 대기"와 동등한 UX). owner는 서버가 요청 생성을 거부하므로
  // 시도하지 않는다 — "대기 중인 승인 요청 없음" 안내로 대체(아래 렌더).
  useEffect(() => {
    if (API_MODE !== 'real' || detailLoading || !detail || detail.pendingApproval || !card || !caseId) return;
    if (role !== 'manager') return;
    const requestable =
      card.primaryAction.requiresApproval &&
      card.primaryAction.state === 'ready' &&
      (card.state === 'risk_review' || card.state === 'returned');
    if (!requestable) return;
    let cancelled = false;
    createApprovalRequest(card.primaryAction.actionId)
      .then(() => (cancelled ? undefined : fetchCaseDetail(caseId)))
      .then((refreshed) => {
        if (!cancelled && refreshed) setDetail(refreshed);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          console.error('[ApprovePage] 승인 요청 자동 생성 실패', err);
          setAutoRequestFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, card, detail, detailLoading, role]);

  // 체크 상태는 라벨 Set — 인덱스 boolean[]의 위치 결합(리셋 effect 취약성, 코드리뷰 A5/D)을 없앤다.
  const [checkedLabels, setCheckedLabels] = useState<Set<string>>(() => new Set());
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [onBehalfChecked, setOnBehalfChecked] = useState(false);
  const [pendingDecision, setPendingDecision] = useState<'approve' | 'reject' | null>(null);
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);

  const usableCount = useMemo(() => {
    if (API_MODE === 'real') return detail?.usableCitationCount ?? 0;
    return sheet ? usableCitations(sheet.citations).length : 0;
  }, [detail, sheet]);

  const guardNote = API_MODE === 'real' ? detail?.guardNote : sheet?.guardNote;

  // 승인 체크리스트(디자인 §2c 4항목) — real 모드는 서버가 이미 갖고 있는 항목(pending
  // approval.checklist)을 우선 쓴다. 없으면(신규 요청 직후 등) mock과 같은 고정 템플릿으로
  // 폴백한다 — 라벨은 케이스 데이터로 채운다.
  const checklistItems: ChecklistItem[] = useMemo(() => {
    if (API_MODE === 'real' && detail?.pendingApproval?.checklist) {
      return detail.pendingApproval.checklist.map((item) => ({ key: item.key, label: item.label }));
    }
    if (!card) return [];
    return [
      {
        key: 'risk',
        label: `위험도·영향 검토 완료 (${card.severity}${card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''})`,
      },
      { key: 'docs', label: `누락 서류·연결 근거 확인 (근거 ${usableCount}건)` },
      { key: 'tone', label: '단정형 표현 없음 · 표현 가이드 준수' },
      {
        key: 'content',
        label: draft ? `${draft.langs.map((v) => v.label).join('/')} 초안 내용 확인` : '요청 내용 확인',
      },
    ];
  }, [card, draft, usableCount, detail]);

  if (!card || (API_MODE !== 'real' && !sheet)) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">케이스를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  // M4 라우트 가드(7단계 §6 "M4: viewer 진입 불가") — 열람자는 최종 승인 화면 자체에 못 들어온다.
  if (role === 'viewer') {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">열람자 권한으로는 최종 승인 화면에 진입할 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toCase(card.caseId)}>
          케이스로 돌아가기
        </Button>
      </div>
    );
  }

  if (API_MODE === 'real' && detailLoading) {
    return (
      <div className="flex min-h-dvh flex-col bg-canvas">
        <BackHeader title="최종 승인" onBack={() => nav.toCase(card.caseId)} />
        <div className="flex flex-1 items-center justify-center p-5">
          <p className="text-body2 text-muted">불러오는 중…</p>
        </div>
      </div>
    );
  }

  const checkedCount = checklistItems.filter((item) => checkedLabels.has(item.label)).length;
  const allChecked = checkedCount === checklistItems.length && checklistItems.length > 0;
  // 고위험(기한 경과 blocked 등)은 승인 대상이 아니다 — 상태 전이 합법성으로 게이트(코드리뷰 A2/B3/F3).
  const approvable = canApproveCase(card, usableCount);
  const citationLocked = isCitationLocked(usableCount);
  const highRiskBlocked = !canTransition(card.state, 'human_approved');
  // 공동대표(7단계 §3.3) — 다른 owner가 이미 결정한 케이스는 PIN 시트 대신 읽기전용 배너.
  const alreadyDecided = card.state === 'human_approved';
  const decidedByActor = alreadyDecided
    ? mergedAuditLog(events).find((e) => e.caseId === card.caseId && e.type === 'approval_decided')?.actor
    : undefined;
  // owner_only 정책 하 manager는 대리 승인(체크박스)이 아니면 직접 승인할 수 없다(§2 각주1).
  const needsOwnerApproval = role === 'manager' && approvalPolicy === 'owner_only' && !onBehalfChecked;
  // real 모드는 실제 위임이 있을 때만 대리 승인 체크박스를 보여준다(7단계 §3.1 "명시적 위임").
  const canShowDelegationCheckbox = role === 'manager' && (API_MODE !== 'real' || myDelegation !== null);
  const noPendingApproval = API_MODE === 'real' && !detailLoading && !detail?.pendingApproval;

  if (alreadyDecided) {
    return (
      <div className="flex min-h-dvh flex-col bg-canvas">
        <BackHeader title="최종 승인" onBack={() => nav.toCase(card.caseId)} />
        <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
          <section className="flex flex-col gap-1.5 rounded-in bg-approvalbg px-3.5 py-3">
            <p className="text-label1 font-semibold text-approval">
              {decidedByActor ? `${decidedByActor}이(가) 이미 결정했습니다` : '이미 결정된 케이스입니다'}
            </p>
            <p className="text-caption1 leading-relaxed text-approval">
              공동대표 정책상 먼저 결정한 1인으로 확정됩니다 — 중복 결정은 필요하지 않습니다.
            </p>
          </section>
          <Button variant="outline" onClick={() => nav.toCaseHistory(card.caseId)}>
            판단 기록 보기
          </Button>
        </main>
      </div>
    );
  }

  if (noPendingApproval && (role !== 'manager' || autoRequestFailed)) {
    return (
      <div className="flex min-h-dvh flex-col bg-canvas">
        <BackHeader title="최종 승인" onBack={() => nav.toCase(card.caseId)} />
        <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
          <p className="text-body2 text-muted">대기 중인 승인 요청이 없습니다.</p>
        </main>
      </div>
    );
  }

  const toggle = (label: string) =>
    setCheckedLabels((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });

  const onBehalfUserId = API_MODE === 'real' && onBehalfChecked ? myDelegation?.delegatorUserId : undefined;
  const onBehalfDisplay = onBehalfChecked ? (API_MODE === 'real' ? myDelegation?.delegatorName : OWNER_NAME) : undefined;

  // 4.3 승인 PIN 목업(mock)/서버 검증(real) — 승인·반려 둘 다 본인확인 이력이 남는 행위(7단계 §4).
  const onApprove = () => {
    setPin('');
    setPinError(null);
    setPendingDecision('approve');
  };
  const onRejectClick = () => {
    if (API_MODE === 'real' && !reason.trim()) {
      setReasonError('반려 사유를 입력해주세요.');
      return;
    }
    setReasonError(null);
    setPin('');
    setPinError(null);
    setPendingDecision('reject');
  };
  const onPinClose = () => {
    setPendingDecision(null);
    setPin('');
    setPinError(null);
  };
  const onPinConfirm = async () => {
    if (!isValidPinFormat(pin)) {
      setPinError('숫자 4자리를 입력하세요.');
      return;
    }
    if (API_MODE !== 'real' && pin !== DEMO_PIN) {
      setPinError('PIN이 일치하지 않습니다. 다시 입력해주세요.');
      setPin('');
      return;
    }
    if (!pendingDecision) return;

    const checklist: DecisionChecklistItem[] = checklistItems.map((item) => ({
      key: item.key,
      label: item.label,
      checked: checkedLabels.has(item.label),
    }));
    const approvalId = detail?.pendingApproval?.id;

    try {
      const ok =
        pendingDecision === 'approve'
          ? await approve({
              card,
              usableCount,
              checklistCount: checklistItems.length,
              checklist,
              onBehalf: onBehalfDisplay,
              onBehalfUserId,
              approvalId,
              pin,
            })
          : await reject({ card, usableCount, reason, onBehalfUserId, approvalId, pin });
      if (!ok) {
        setPinError('처리하지 못했습니다. 다시 시도해주세요.');
        return;
      }
      const decision = pendingDecision;
      setPendingDecision(null);
      if (decision === 'approve') nav.toCaseHistory(card.caseId);
      else nav.toHome();
    } catch (err) {
      setPinError(err instanceof ApiError ? err.message : '처리 중 오류가 발생했습니다.');
    }
  };
  // owner_only 정책 하 manager의 "대표 승인 요청" — 결정이 아니라 요청 기록만 남긴다.
  const onRequestOwnerApproval = async () => {
    await requestOwnerApproval(card);
    nav.toHome();
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="최종 승인" onBack={() => nav.toCase(card.caseId)} />

      {!isOnline && <OfflineBanner />}

      <main className="flex flex-1 flex-col gap-5 px-5 pb-40 pt-4">
        <section className="flex flex-col gap-1 rounded-in bg-warnbg px-3.5 py-3">
          <p className="text-safety font-bold text-warning">{SAFETY_NOTICE_TEXT}</p>
          <p className="text-caption1 leading-relaxed text-medium">
            승인 완료 시 발송 실행이 가능해지며, 승인자는 판단 기록에 남습니다.
          </p>
        </section>

        {/* 고위험 케이스 안내 — 앱 승인 불가, 행정사 전달 전용(GOTCHAS 고위험 처리 버튼 금지). */}
        {highRiskBlocked && guardNote && (
          <section className="flex flex-col gap-1 rounded-in bg-approvalbg px-3.5 py-3">
            <p className="text-label1 font-semibold text-approval">이 케이스는 앱에서 승인할 수 없습니다</p>
            <p className="text-caption1 leading-relaxed text-approval">{guardNote}</p>
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
              필수 {checkedCount}/{checklistItems.length}
            </span>
          </div>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {checklistItems.map((item) => (
              <li key={item.key} className="border-b border-hairline last:border-none">
                <label className="flex min-h-12 cursor-pointer items-center gap-2.5 px-3 py-2.5">
                  <input
                    type="checkbox"
                    checked={checkedLabels.has(item.label)}
                    onChange={() => toggle(item.label)}
                    className="size-4 accent-primary"
                  />
                  <span className="text-label1 text-ink">{item.label}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>

        {canShowDelegationCheckbox && (
          <section className="flex flex-col gap-1.5">
            <h3 className="text-caption1 font-bold text-subtle">대리 승인</h3>
            <label className="flex min-h-12 cursor-pointer items-center gap-2.5 rounded-in border border-hairline px-3 py-2.5">
              <input
                type="checkbox"
                checked={onBehalfChecked}
                onChange={(event) => setOnBehalfChecked(event.target.checked)}
                className="size-4 accent-primary"
              />
              <span className="text-label1 text-ink">
                대리 승인으로 처리{' '}
                <span className="text-dim">
                  (위임: {API_MODE === 'real' ? (myDelegation?.delegatorName ?? OWNER_NAME) : OWNER_NAME})
                </span>
              </span>
            </label>
            <p className="text-caption1 text-dim">대표님이 부재중일 때 위임받아 승인하는 경우에만 체크하세요.</p>
          </section>
        )}

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">
            의견 / 반려 사유 {API_MODE !== 'real' && <span className="font-medium text-dim">(선택)</span>}
          </h3>
          <textarea
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              setReasonError(null);
            }}
            placeholder="추가 의견이 있으면 입력하세요."
            aria-label="의견 / 반려 사유"
            className="h-16 rounded-in bg-canvas px-3 py-2.5 text-label1 text-ink shadow-outline outline-none placeholder:text-faint focus:shadow-rail-focus"
          />
          {reasonError && <p className="text-caption1 text-critical-text">{reasonError}</p>}
        </section>
      </main>

      <footer className="fixed inset-x-0 bottom-0 flex flex-col gap-2 border-t border-hairline bg-canvas px-5 py-3">
        {/* owner_only 정책(7단계 §2 각주1) — manager는 대리 승인 체크 없이는 직접 승인 대신 요청만. */}
        <Button
          variant="primary"
          className="w-full"
          disabled={!allChecked || citationLocked || !approvable || !isOnline}
          onClick={needsOwnerApproval ? onRequestOwnerApproval : onApprove}
        >
          {needsOwnerApproval ? '대표 승인 요청' : '승인하기'}
        </Button>
        <Button variant="outline" size="sm" className="w-full" disabled={!isOnline} onClick={onRejectClick}>
          반려하기
        </Button>
        <p className="text-center text-caption1 text-dim">반려 시 사유가 판단 기록에 남고 요청이 되돌아갑니다.</p>
      </footer>

      <BottomSheet
        open={pendingDecision !== null}
        onClose={onPinClose}
        footer={
          <Button variant="primary" className="w-full" onClick={() => void onPinConfirm()}>
            확인
          </Button>
        }
      >
        <h3 className="mb-2 text-body1 font-semibold text-ink">본인확인 PIN</h3>
        <p className="mb-4 text-body2 leading-relaxed text-muted">
          {pendingDecision === 'reject' ? '반려는' : '승인은'} 본인확인 이력이 남는 행위입니다. PIN 4자리를
          입력해주세요.
          {API_MODE !== 'real' && ` (데모 PIN: ${DEMO_PIN})`}
        </p>
        <input
          type="text"
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={(event) => {
            setPin(event.target.value);
            setPinError(null);
          }}
          placeholder="••••"
          aria-label="본인확인 PIN"
          autoFocus
          className="h-12 w-full rounded-in bg-canvas px-3 text-center text-heading2 tracking-[0.5em] text-ink shadow-outline outline-none focus:shadow-rail-focus"
        />
        {pinError && <p className="mt-2 text-caption1 text-critical-text">{pinError}</p>}
      </BottomSheet>
    </div>
  );
}
