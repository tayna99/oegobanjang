import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { BottomSheet } from '@/components/BottomSheet';
import { Button } from '@/components/Button';
import { SAFETY_NOTICE_TEXT } from '@/components/SafetyNotice';
import { useApprovalActions, canApproveCase, isCitationLocked, OWNER_NAME } from '@/lib/approval';
import { approveApproval, createApprovalRequest, rejectApproval, type DecisionBody } from '@/lib/api/approvals';
import { mergedAuditLog } from '@/lib/audit';
import { ApiError } from '@/lib/api/client';
import { USE_REAL_API } from '@/lib/api/config';
import { useSeedCases } from '@/lib/dataSeed';
import { dDayLabel } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { DEMO_PIN, isValidPinFormat } from '@/lib/pin';
import { CASE_SHEETS, type CaseSheet } from '@/mocks/fixtures';
import { draftForCase } from '@/mocks/drafts';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { usableCitations } from '@/stores/citationStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import { useSessionStore } from '@/stores/sessionStore';
import type { CaseCard } from '@/types';
import { cn } from '@/lib/cn';

// real API 모드에서 실패 응답의 사용자 가시 메시지를 뽑는다 — FastAPI의 {detail: string} 관례.
function errorDetail(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.body && typeof err.body === 'object' && 'detail' in err.body) {
    const { detail } = err.body as { detail: unknown };
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

// 2c 최종 승인 — reference/design-system/외고반장 Mobile.dc.html §2c(145~186행) 이식(M2.6.3).
// 성급한 승인 방지 게이트가 "스트리밍 완료"에서 "사람 체크리스트 필수 N/N"으로 교체된다
// (블루프린트 §2 개정). citation-0 잠금(GOTCHAS §2)·상태 전이 합법성이 이중 게이트.
// 승인/반려 결정 자체는 useApprovalActions 공유 유닛이 수행한다(코드리뷰 A/B/F 근본 교정).

export function ApprovePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const { approve, reject, requestOwnerApproval } = useApprovalActions();
  const role = useRoleStore((s) => s.role);
  const approvalPolicy = useCompanyStore((s) => s.approvalPolicy);
  const events = useEvidenceStore((s) => s.events);
  const delegatedBy = useSessionStore((s) => s.delegatedBy);

  useSeedCases();

  const card = caseId ? cases[caseId] : undefined;
  // real 모드는 CASE_SHEETS(mock 픽스처, 'nguyen' 등)에 실 케이스 id('cs_nguyen' 등)가 없어
  // 항상 undefined다 — 값을 지어내지 않고, 아직 안 내려오는 필드만 빈 채로 둔 최소 CaseSheet로
  // 대체한다(근거 라이브러리·체크리스트 완전 동기화는 2.5류 후속, HANDOFF 참고).
  const usingSyntheticSheet = USE_REAL_API && card !== undefined && CASE_SHEETS[caseId ?? ''] === undefined;
  const syntheticSheet = useMemo<CaseSheet>(
    () => ({ caseId: caseId ?? '', summary: '', checkedItems: [], citations: [], activity: [] }),
    [caseId],
  );
  const sheet: CaseSheet | undefined = caseId ? (CASE_SHEETS[caseId] ?? (usingSyntheticSheet ? syntheticSheet : undefined)) : undefined;
  const draft = draftForCase(caseId);

  // 승인 체크리스트(디자인 §2c 4항목) — 라벨은 케이스 데이터로 채우는 고정 템플릿.
  const checklist = useMemo(() => {
    if (!card || !sheet) return [] as string[];
    const evidenceLine = usingSyntheticSheet
      ? '누락 서류·연결 근거 확인' // real 모드는 근거 수를 아직 안 내려준다 — 개수를 지어내지 않는다.
      : `누락 서류·연결 근거 확인 (근거 ${usableCitations(sheet.citations).length}건)`;
    return [
      `위험도·영향 검토 완료 (${card.severity}${card.dDay !== undefined ? ` · ${dDayLabel(card.dDay)}` : ''})`,
      evidenceLine,
      '단정형 표현 없음 · 표현 가이드 준수',
      draft ? `${draft.langs.map((v) => v.label).join('/')} 초안 내용 확인` : '요청 내용 확인',
    ];
  }, [card, sheet, draft, usingSyntheticSheet]);

  // 체크 상태는 라벨 Set — 인덱스 boolean[]의 위치 결합(리셋 effect 취약성, 코드리뷰 A5/D)을 없앤다.
  const [checkedLabels, setCheckedLabels] = useState<Set<string>>(() => new Set());
  const [reason, setReason] = useState('');
  const [onBehalfChecked, setOnBehalfChecked] = useState(false);
  const [pinOpen, setPinOpen] = useState(false);
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);
  // real 모드 전용 — 어떤 결정을 확정하려는 PIN 시트인지(반려도 서버가 본인확인을 요구한다,
  // mock과 달리 — services/approvals.py "본인확인 수단 필수... approve·reject 공통").
  const [pendingDecision, setPendingDecision] = useState<'approved' | 'rejected'>('approved');
  const [submitting, setSubmitting] = useState(false);

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

  const checkedCount = checklist.filter((label) => checkedLabels.has(label)).length;
  const allChecked = checkedCount === checklist.length && checklist.length > 0;
  // 고위험(기한 경과 blocked 등)은 승인 대상이 아니다 — 상태 전이 합법성으로 게이트(코드리뷰 A2/B3/F3).
  // real 모드는 근거 데이터가 아직 없어 citation-0 판정을 클라이언트에서 흉내내지 않는다(빈
  // citations로 계산하면 늘 "잠김"이 나와 버튼이 영구 비활성화된다) — 서버가 실제 게이트를
  // 담당하고, 걸리면 4xx 에러 배너로 드러난다.
  const approvable = usingSyntheticSheet ? canTransition(card.state, 'human_approved') : canApproveCase(card, sheet);
  const citationLocked = usingSyntheticSheet ? false : isCitationLocked(sheet);
  const highRiskBlocked = !canTransition(card.state, 'human_approved');
  // 공동대표(7단계 §3.3) — 다른 owner가 이미 결정한 케이스는 PIN 시트 대신 읽기전용 배너.
  const alreadyDecided = card.state === 'human_approved';
  const decidedByActor = alreadyDecided
    ? mergedAuditLog(events).find((e) => e.caseId === card.caseId && e.type === 'approval_decided')?.actor
    : undefined;
  // owner_only 정책 하 manager는 대리 승인(체크박스)이 아니면 직접 승인할 수 없다(§2 각주1).
  const needsOwnerApproval = role === 'manager' && approvalPolicy === 'owner_only' && !onBehalfChecked;

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

  const toggle = (label: string) =>
    setCheckedLabels((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });

  // real 모드 승인/반려 — 서버가 유일한 진실 원천이다. approval_id는 이미 대기 중인 게 있으면
  // 그걸 쓰고(카드 목록 조회 시 이미 내려온 값), 없으면(manager만 가능, 백엔드 request_approval
  // 권한 제약과 동일) 새로 생성한다.
  const submitRealDecision = async () => {
    if (submitting) return;
    let approvalId = card.primaryAction.pendingApprovalId;
    if (!approvalId && role !== 'manager') {
      setPinError('아직 생성된 승인 요청이 없습니다.');
      return;
    }
    setSubmitting(true);
    setPinError(null);
    try {
      if (!approvalId) {
        const created = await createApprovalRequest(card.primaryAction.actionId);
        approvalId = created.approval.id;
      }
      const delegate = role === 'manager' && onBehalfChecked ? delegatedBy[0] : undefined;
      const body: DecisionBody = {
        idempotencyKey: crypto.randomUUID(),
        identityMethod: 'pin',
        pin,
        onBehalfOfUserId: delegate?.userId,
        reason: pendingDecision === 'rejected' ? reason || undefined : undefined,
      };
      const response =
        pendingDecision === 'approved' ? await approveApproval(approvalId, body) : await rejectApproval(approvalId, body);
      useCaseStore.getState().upsert({ ...card, state: response.case_state as CaseCard['state'] });
      setPinOpen(false);
      if (pendingDecision === 'approved') nav.toCaseHistory(card.caseId);
      else nav.toHome();
    } catch (err) {
      setPinError(errorDetail(err, '요청을 처리하지 못했습니다.'));
    } finally {
      setSubmitting(false);
    }
  };

  // 4.3 승인 PIN 목업 — 승인은 본인확인 이력이 남는 행위(7단계 §4). 세션만으로는 승인 불가.
  const onApprove = () => {
    setPin('');
    setPinError(null);
    setPendingDecision('approved');
    setPinOpen(true);
  };
  const onPinClose = () => {
    setPinOpen(false);
    setPin('');
    setPinError(null);
  };
  const onPinConfirm = () => {
    if (!isValidPinFormat(pin)) {
      setPinError('숫자 4자리를 입력하세요.');
      return;
    }
    if (USE_REAL_API) {
      void submitRealDecision();
      return;
    }
    if (pin !== DEMO_PIN) {
      setPinError('PIN이 일치하지 않습니다. 다시 입력해주세요.');
      setPin('');
      return;
    }
    const onBehalf = role === 'manager' && onBehalfChecked ? OWNER_NAME : undefined;
    if (approve({ card, sheet, checklistCount: checklist.length, onBehalf })) {
      setPinOpen(false);
      nav.toCaseHistory(card.caseId);
    }
  };
  // owner_only 정책 하 manager의 "대표 승인 요청" — 결정이 아니라 요청 기록만 남긴다.
  const onRequestOwnerApproval = () => {
    requestOwnerApproval(card);
    nav.toHome();
  };
  const onReject = () => {
    if (USE_REAL_API) {
      // mock과 달리 서버는 반려도 본인확인을 요구한다(services/approvals.py 공통 게이트) —
      // 같은 PIN 시트를 반려 결정용으로 재사용한다.
      setPin('');
      setPinError(null);
      setPendingDecision('rejected');
      setPinOpen(true);
      return;
    }
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

        {role === 'manager' && (
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
                <span className="text-dim">(위임: {USE_REAL_API ? (delegatedBy[0]?.name ?? '없음') : OWNER_NAME})</span>
              </span>
            </label>
            <p className="text-caption1 text-dim">대표님이 부재중일 때 위임받아 승인하는 경우에만 체크하세요.</p>
          </section>
        )}

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
        {/* owner_only 정책(7단계 §2 각주1) — manager는 대리 승인 체크 없이는 직접 승인 대신 요청만. */}
        <Button
          variant="primary"
          className="w-full"
          disabled={!allChecked || citationLocked || !approvable}
          onClick={needsOwnerApproval ? onRequestOwnerApproval : onApprove}
        >
          {needsOwnerApproval ? '대표 승인 요청' : '승인하기'}
        </Button>
        <Button variant="outline" size="sm" className="w-full" onClick={onReject}>
          반려하기
        </Button>
        <p className="text-center text-caption1 text-dim">반려 시 사유가 판단 기록에 남고 요청이 되돌아갑니다.</p>
      </footer>

      <BottomSheet
        open={pinOpen}
        onClose={onPinClose}
        footer={
          <Button variant="primary" className="w-full" onClick={onPinConfirm} disabled={submitting}>
            {submitting ? '처리 중…' : '확인'}
          </Button>
        }
      >
        <h3 className="mb-2 text-body1 font-semibold text-ink">본인확인 PIN</h3>
        <p className="mb-4 text-body2 leading-relaxed text-muted">
          {pendingDecision === 'rejected' ? '반려는' : '승인은'} 본인확인 이력이 남는 행위입니다. PIN 4자리를
          입력해주세요. (데모 PIN: {DEMO_PIN})
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
