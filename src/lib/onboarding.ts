import { ACTOR_NAME } from '@/lib/approval';
import { ROLE_LABEL } from '@/lib/role';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { Role } from '@/types';

// 온보딩(4.1) 완료 오케스트레이션 — lib/company.ts와 동일한 분리 원칙(스토어 갱신 +
// evidence 기록을 한 곳에서). O4는 "첫 근로자 1명"을 등록하는 화면이지만, 앱의 데모
// 세계관은 이미 6인 로스터를 전제하므로(O3 "E-9 근로자 수: 6명") 전체 로스터를
// 멱등 upsert한다 — BriefingHomePage의 자체 시드와 caseId가 겹쳐도 안전하다.
// 신규 EvidenceType을 만들지 않고 기존 'plan_created'(감사 로그 "계획 생성")를 재사용한다
// (audit.ts의 두 Record를 건드리지 않기 위함 — 코드리뷰 F1급 중복 방지 원칙과 동일).
export interface OnboardingActions {
  completeOnboarding: (role: Role) => void;
}

export function useOnboardingActions(): OnboardingActions {
  const upsert = useCaseStore((s) => s.upsert);
  const appendEvidence = useEvidenceStore((s) => s.append);

  return {
    completeOnboarding: (role) => {
      CASE_CARDS.forEach(upsert);
      appendEvidence({
        id: `onboarding-completed-${Date.now()}`,
        type: 'plan_created',
        at: new Date().toISOString(),
        summary: '온보딩 완료 — 근로자 등록 · 첫 브리핑 생성',
        actor: `${ROLE_LABEL[role]} ${ACTOR_NAME[role]}`,
      });
    },
  };
}
