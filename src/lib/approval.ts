import { useCaseStore, canTransition } from '@/stores/caseStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import { usableCitations } from '@/stores/citationStore';
import { RUN_CONFIGS } from '@/mocks/runs';
import { ROLE_LABEL } from '@/lib/role';
import type { CaseCard, Role } from '@/types';
import type { CaseSheet } from '@/mocks/fixtures';

// 승인/반려 생애주기의 단일 출처(코드리뷰 A/B/F 근본 원인 교정).
// ApprovePage·(향후 PC 워크벤치)가 모두 이 유닛을 호출해 동일하게 결정한다 —
// request→decide→transition→evidence 코레오그래피를 화면마다 인라인 복제하지 않는다.

// 데모 담당자 페르소나 — evidence actor의 단일 출처(코드리뷰 A/F actor 일관성).
export const CURRENT_USER = '김담당';
// 데모 대표 페르소나(4.2 역할 모델) — owner로 전환 시 승인자 표시명.
export const OWNER_NAME = '김대표';
// 역할별 승인자 표시명 — viewer는 승인 자체가 불가(매트릭스 §2 "승인/반려: viewer –")라
// 실제 경로를 타지 않지만 Record 완전성을 위해 채운다.
const ACTOR_NAME: Record<Role, string> = { manager: CURRENT_USER, owner: OWNER_NAME, viewer: '최감사' };
// M8 "누가(역할)·언제·본인/대리"(7단계 §5) — actor 문자열에 역할 라벨을 접두한다.
function actorLabel(role: Role, suffix: string): string {
  return `${ROLE_LABEL[role]} ${ACTOR_NAME[role]} (${suffix})`;
}

// 케이스의 승인 판단 기록 번호 — RUN_CONFIGS(approval)에서 파생. 하드코딩 금지(코드리뷰 F1).
export function approvalRefFor(caseId: string): string | undefined {
  return RUN_CONFIGS.find((config) => config.caseId === caseId && config.mode === 'approval')?.evidenceRef;
}

// F등급(합성) 제외한 실사용 근거 0건이면 승인 잠금(GOTCHAS §2).
export function isCitationLocked(sheet: CaseSheet): boolean {
  return usableCitations(sheet.citations).length === 0;
}

// 사람 승인이 가능한 상태인가 — 상태 전이 합법성이 CTA를 게이트한다(코드리뷰 A2/B3/F3).
// blocked(고위험 전달 전용)·human_approved·completed는 승인 불가 → CTA 비활성.
export function canApproveCase(card: CaseCard, sheet: CaseSheet): boolean {
  return canTransition(card.state, 'human_approved') && !isCitationLocked(sheet);
}

interface DecisionInput {
  card: CaseCard;
  sheet: CaseSheet;
  reason?: string;
  checklistCount?: number;
  /** 대리 승인 시 위임자명(예: OWNER_NAME) — 없으면 본인 처리(4.3, 7단계 §3.1 배지 규약). */
  onBehalf?: string;
}

export interface ApprovalActions {
  approve: (input: DecisionInput) => boolean;
  reject: (input: DecisionInput) => boolean;
  /** 반려된(returned) 케이스를 재검토 위해 승인 대기로 되돌린다 — 재승인 크래시 방지(코드리뷰 A1/B2). */
  reopenForReview: (card: CaseCard) => void;
}

export function useApprovalActions(): ApprovalActions {
  const transition = useCaseStore((s) => s.transition);
  const upsert = useCaseStore((s) => s.upsert);
  const requestApproval = useApprovalStore((s) => s.requestApproval);
  const decide = useApprovalStore((s) => s.decide);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const role = useRoleStore((s) => s.role);
  const actorName = ACTOR_NAME[role];

  // 결정 전에 approval을 항상 pending으로 리셋 — 이전 시도가 terminal(rejected/approved)이면
  // decide가 throw하므로(코드리뷰 A1/B2), 새 시도마다 fresh requestApproval.
  const ensurePending = (actionId: string) => {
    const current = useApprovalStore.getState().approvals[actionId];
    if (!current || current.status !== 'pending') requestApproval(actionId);
  };

  return {
    approve: ({ card, sheet, checklistCount, onBehalf }) => {
      if (!canApproveCase(card, sheet)) return false; // 방어: 게이트 우회 차단
      const actionId = card.primaryAction.actionId;
      const ref = approvalRefFor(card.caseId);
      ensurePending(actionId);
      decide(actionId, 'approved', `${actionId}:${ref ?? card.caseCode}:approved`);
      appendEvidence({
        id: `${card.caseId}-checklist-completed`,
        type: 'checklist_completed',
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        summary: `필수 ${checklistCount ?? 0}항목 확인 · 근거 ${usableCitations(sheet.citations).length}건 연결 확인`,
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

    reject: ({ card, reason }) => {
      if (!canTransition(card.state, 'returned')) return false;
      const actionId = card.primaryAction.actionId;
      ensurePending(actionId);
      // 키에 사유를 포함 — 사유가 바뀐 재반려가 no-op으로 유실되지 않게(코드리뷰 A6).
      decide(actionId, 'rejected', `${actionId}:rejected:${reason ?? ''}`, reason || undefined);
      appendEvidence({
        // 사유별로 다른 id — 재반려가 append no-op으로 삼켜지지 않게.
        id: `${actionId}-rejected:${reason ?? ''}`,
        type: 'approval_rejected', // 승인과 구분(감사 타임라인이 '반려'로 표기, 코드리뷰 A3)
        at: new Date().toISOString(),
        caseId: card.caseId,
        actionId,
        summary: reason ? '반려 · 사유 기록됨' : '반려',
        actor: actorLabel(role, '본인 확인 완료'),
      });
      transition(card.caseId, 'returned');
      return true;
    },

    reopenForReview: (card) => {
      if (card.state !== 'returned') return;
      transition(card.caseId, 'approval_pending');
      requestApproval(card.primaryAction.actionId); // fresh pending 승인 요청
    },
  };
}
