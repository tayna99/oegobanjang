import { useCaseStore, canTransition } from '@/stores/caseStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import { RUN_CONFIGS } from '@/mocks/runs';
import { ROLE_LABEL } from '@/lib/role';
import { API_MODE } from '@/lib/api/config';
import { approveApproval, createApprovalRequest, rejectApproval, type DecisionChecklistItem } from '@/lib/api/approvals';
import { fetchEvidence } from '@/lib/api/evidence';
import type { CaseCard, Role } from '@/types';

// 승인/반려 생애주기의 단일 출처(코드리뷰 A/B/F 근본 원인 교정).
// ApprovePage·(향후 PC 워크벤치)가 모두 이 유닛을 호출해 동일하게 결정한다 —
// request→decide→transition→evidence 코레오그래피를 화면마다 인라인 복제하지 않는다.
// R2.4 — mock 분기는 기존 동기 변이를 그대로 유지하고, real 분기만 서버 확인 후 반영한다
// (GOTCHAS §2: 승인은 낙관적 갱신 금지). API_MODE 분기점은 이 파일 하나로 유지한다
// (sessionStore/evidenceStore와 동일 관례 — "액션 시그니처는 그대로, 내부 구현만 분기").

// 데모 담당자 페르소나 — evidence actor의 단일 출처(코드리뷰 A/F actor 일관성).
export const CURRENT_USER = '김담당';
// 데모 대표 페르소나(4.2 역할 모델) — owner로 전환 시 승인자 표시명.
export const OWNER_NAME = '김대표';
// 역할별 승인자 표시명 — viewer는 승인 자체가 불가(매트릭스 §2 "승인/반려: viewer –")라
// 실제 경로를 타지 않지만 Record 완전성을 위해 채운다. lib/company.ts도 구성원/위임 evidence
// actor에 재사용(데모 페르소나 이름의 단일 출처를 여기 하나로 유지).
export const ACTOR_NAME: Record<Role, string> = { manager: CURRENT_USER, owner: OWNER_NAME, viewer: '최감사' };
// M8 "누가(역할)·언제·본인/대리"(7단계 §5) — actor 문자열에 역할 라벨을 접두한다.
function actorLabel(role: Role, suffix: string): string {
  return `${ROLE_LABEL[role]} ${ACTOR_NAME[role]} (${suffix})`;
}

// 케이스의 승인 판단 기록 번호 — RUN_CONFIGS(approval)에서 파생. 하드코딩 금지(코드리뷰 F1).
export function approvalRefFor(caseId: string): string | undefined {
  return RUN_CONFIGS.find((config) => config.caseId === caseId && config.mode === 'approval')?.evidenceRef;
}

// F등급(합성) 제외한 실사용 근거 수 — mock은 usableCitations(sheet.citations).length, real은
// 서버 usable_citation_count를 그대로 넘긴다(둘 다 CaseSheet 없이 이 파일이 동작하게 한다, R2.4).
export function isCitationLocked(usableCount: number): boolean {
  return usableCount === 0;
}

// 사람 승인이 가능한 상태인가 — 상태 전이 합법성이 CTA를 게이트한다(코드리뷰 A2/B3/F3).
// blocked(고위험 전달 전용)·human_approved·completed는 승인 불가 → CTA 비활성.
export function canApproveCase(card: CaseCard, usableCount: number): boolean {
  return canTransition(card.state, 'human_approved') && !isCitationLocked(usableCount);
}

interface DecisionInput {
  card: CaseCard;
  usableCount: number;
  reason?: string;
  checklistCount?: number;
  /** real 모드 전용 — 서버 제출용 체크리스트(전 항목 checked:true, ApprovePage가 조립). */
  checklist?: DecisionChecklistItem[];
  /** mock 모드 대리 승인 표시명(예: OWNER_NAME) — 없으면 본인 처리(4.3, 7단계 §3.1 배지 규약). */
  onBehalf?: string;
  /** real 모드 대리 승인 위임자 실제 user id(GET /delegations/mine에서 얻음). */
  onBehalfUserId?: string;
  /** real 모드 서버 승인 id — 없으면 결정 자체가 불가(화면이 먼저 확보해야 함). */
  approvalId?: string;
  /** real 모드 PIN — 서버가 users.pin_hash와 대조 검증한다. */
  pin?: string;
}

export interface ApprovalActions {
  approve: (input: DecisionInput) => Promise<boolean>;
  reject: (input: DecisionInput) => Promise<boolean>;
  /** 반려된(returned) 케이스를 재검토 위해 승인 대기로 되돌린다 — 재승인 크래시 방지(코드리뷰 A1/B2). */
  reopenForReview: (card: CaseCard) => Promise<void>;
  /** owner_only 정책 하 manager의 "대표 승인 요청"(7단계 §2 각주1) — 상태 전이는 없다,
   * 요청 기록만 남기고 owner의 결정을 기다린다. */
  requestOwnerApproval: (card: CaseCard) => Promise<void>;
}

export function useApprovalActions(): ApprovalActions {
  const transition = useCaseStore((s) => s.transition);
  const upsert = useCaseStore((s) => s.upsert);
  const requestApproval = useApprovalStore((s) => s.requestApproval);
  const decide = useApprovalStore((s) => s.decide);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const hydrateEvidence = useEvidenceStore((s) => s.hydrate);
  const role = useRoleStore((s) => s.role);
  const actorName = ACTOR_NAME[role];

  // 결정 전에 approval을 항상 pending으로 리셋 — 이전 시도가 terminal(rejected/approved)이면
  // decide가 throw하므로(코드리뷰 A1/B2), 새 시도마다 fresh requestApproval.
  const ensurePending = (actionId: string) => {
    const current = useApprovalStore.getState().approvals[actionId];
    if (!current || current.status !== 'pending') requestApproval(actionId);
  };

  // real 모드 — 서버가 이미 결정을 확정한 뒤, 로컬 스토어(approvalStore/caseStore)를 그
  // 결과로 미러링한다. DispatchQueuePage·lib/dispatch.deriveDispatchQueue가 approvalStore를
  // 읽으므로 이 미러링은 생략할 수 없다.
  const mirrorLocalDecision = (card: CaseCard, actionId: string, decision: 'approved' | 'rejected') => {
    ensurePending(actionId);
    decide(actionId, decision, `${actionId}:${decision}:${Date.now()}`);
    transition(card.caseId, decision === 'approved' ? 'human_approved' : 'returned');
    if (decision === 'approved') {
      const updated = useCaseStore.getState().cases[card.caseId];
      if (updated) upsert({ ...updated, agentStage: 'executed' });
    }
  };

  // 서버가 자기 트랜잭션에서 이미 기록한 결정 evidence(approval_decided/approval_rejected 등)를
  // 다시 로컬에서 append하지 않고, 대신 서버 상태를 다시 읽어 evidenceStore를 재동기화한다.
  const resyncEvidence = () => {
    fetchEvidence()
      .then(hydrateEvidence)
      .catch((err: unknown) => console.error('[approval] evidence 재동기화 실패', err));
  };

  return {
    approve: async ({ card, usableCount, checklistCount, checklist, onBehalf, onBehalfUserId, approvalId, pin }) => {
      if (!canApproveCase(card, usableCount)) return false; // 방어: 게이트 우회 차단
      const actionId = card.primaryAction.actionId;

      if (API_MODE === 'real') {
        if (!approvalId) return false; // 화면이 먼저 승인 id를 확보해야 한다(fetchCaseDetail)
        appendEvidence({
          id: `${card.caseId}-checklist-completed`,
          type: 'checklist_completed',
          at: new Date().toISOString(),
          caseId: card.caseId,
          actionId,
          summary: `필수 ${checklistCount ?? 0}항목 확인 · 근거 ${usableCount}건 연결 확인`,
          actor: `${ROLE_LABEL[role]} ${actorName}`,
        });
        await approveApproval(approvalId, {
          idempotencyKey: `${actionId}:${Date.now()}`,
          identityMethod: 'pin',
          pin,
          onBehalfOfUserId: onBehalfUserId,
          checklist: checklist?.map((item) => ({ ...item, checked: true })),
        });
        mirrorLocalDecision(card, actionId, 'approved');
        resyncEvidence();
        return true;
      }

      // mock 분기 — 기존 동작 그대로(동기 변이, 즉시 resolve).
      const ref = approvalRefFor(card.caseId);
      ensurePending(actionId);
      decide(actionId, 'approved', `${actionId}:${ref ?? card.caseCode}:approved`);
      appendEvidence({
        id: `${card.caseId}-checklist-completed`,
        type: 'checklist_completed',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        summary: `필수 ${checklistCount ?? 0}항목 확인 · 근거 ${usableCount}건 연결 확인`,
        actor: `${ROLE_LABEL[role]} ${actorName}`,
      });
      appendEvidence({
        id: `${actionId}-approved`,
        type: 'approval_decided',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        evidenceRef: ref,
        summary: '승인 확정 · 발송 실행 가능 상태로 전환',
        // 결정자(역할 포함)·본인/대리 기록(4.3, 7단계 §3.1·§5 approval_granted 규약).
        actor: onBehalf ? actorLabel(role, `대리 승인 · 위임: ${onBehalf}`) : actorLabel(role, '본인 확인 완료'),
      });
      transition(card.caseId, 'human_approved');
      // 파이프라인 단계도 실행으로 전진 — 안 하면 "승인 대기 N"이 큐와 모순(코드리뷰 A4).
      const updated = useCaseStore.getState().cases[card.caseId];
      if (updated) upsert({ ...updated, agentStage: 'executed' });
      return true;
    },

    reject: async ({ card, reason, approvalId, pin, onBehalfUserId }) => {
      if (!canTransition(card.state, 'returned')) return false;
      const actionId = card.primaryAction.actionId;

      if (API_MODE === 'real') {
        // DB 정본이 반려도 사유 필수로 요구한다(§5.3-2 CHECK) — 서버 왕복 없이 먼저 막는다.
        if (!reason || !reason.trim()) return false;
        if (!approvalId) return false;
        await rejectApproval(approvalId, {
          idempotencyKey: `${actionId}:rejected:${Date.now()}`,
          identityMethod: 'pin',
          pin,
          onBehalfOfUserId: onBehalfUserId,
          reason,
        });
        mirrorLocalDecision(card, actionId, 'rejected');
        resyncEvidence();
        return true;
      }

      // mock 분기 — 기존 동작 그대로.
      ensurePending(actionId);
      // 키에 사유를 포함 — 사유가 바뀐 재반려가 no-op으로 유실되지 않게(코드리뷰 A6).
      decide(actionId, 'rejected', `${actionId}:rejected:${reason ?? ''}`, reason || undefined);
      // 같은 사유로 반려→보완→재반려하면 사유만으로는 id가 같아 evidenceStore의 id 중복
      // 방지에 걸려 두 번째 반려 기록이 조용히 유실된다(NEXT_ROADMAP B-1) — 같은 actionId의
      // 기존 반려 건수를 순번으로 붙여 매 반려마다 고유한 id를 보장한다.
      const rejectionSeq = useEvidenceStore
        .getState()
        .events.filter((e) => e.type === 'approval_rejected' && e.actionId === actionId).length;
      appendEvidence({
        id: `${actionId}-rejected:${reason ?? ''}:${rejectionSeq}`,
        type: 'approval_rejected', // 승인과 구분(감사 타임라인이 '반려'로 표기, 코드리뷰 A3)
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        summary: reason ? '반려 · 사유 기록됨' : '반려',
        // 반려도 이제 PIN 게이트를 거친다(사용자 결정 — DB 정본과 UX 통일, R2.4) — "본인
        // 확인 완료" 표기는 그 PIN 확인이 실제로 일어났음을 정확히 반영한다.
        actor: actorLabel(role, '본인 확인 완료'),
      });
      transition(card.caseId, 'returned');
      return true;
    },

    reopenForReview: async (card) => {
      if (card.state !== 'returned') return;
      if (API_MODE === 'real') {
        try {
          await createApprovalRequest(card.primaryAction.actionId);
        } catch (err) {
          console.error('[approval] 재검토 승인 요청 실패', err);
          return;
        }
      }
      transition(card.caseId, 'approval_pending');
      requestApproval(card.primaryAction.actionId); // fresh pending 승인 요청
    },

    requestOwnerApproval: async (card) => {
      if (API_MODE === 'real') {
        try {
          await createApprovalRequest(card.primaryAction.actionId);
        } catch (err) {
          console.error('[approval] 대표 승인 요청 실패', err);
          return;
        }
        resyncEvidence();
        return;
      }
      appendEvidence({
        id: `${card.caseId}-owner-approval-requested-${Date.now()}`,
        type: 'approval_requested',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId: card.primaryAction.actionId,
        summary: '담당자가 대표 승인을 요청함(회사 정책: owner_only)',
        actor: actorLabel(role, '요청'),
      });
    },
  };
}
