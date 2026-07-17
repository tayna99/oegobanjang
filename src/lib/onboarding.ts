import { ACTOR_NAME } from '@/lib/approval';
import { ROLE_LABEL } from '@/lib/role';
import { workerToCard } from '@/lib/csvUpload';
import type { WorkerInput } from '@/lib/csvUpload';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CompanyProfile, Role } from '@/types';

// 온보딩(4.1) 완료 오케스트레이션 — lib/company.ts와 동일한 분리 원칙(스토어 갱신 +
// evidence 기록을 한 곳에서). O4는 "첫 근로자 1명"을 등록하는 화면이고(R1.2), 앱의 데모
// 세계관은 이미 6인 로스터를 전제하므로(O3 "E-9 근로자 수: 6명") 전체 로스터도 함께
// 멱등 upsert한다 — BriefingHomePage의 자체 시드와 caseId가 겹쳐도 안전하다. O4에서
// 입력한 근로자는 CSV(4.4)와 동일한 데이터 계약(lib/csvUpload.workerToCard)으로 별도
// caseId(onboard- 접두)에 반영해 입력이 실제로 버려지지 않게 한다(R1.2, NEXT_ROADMAP M-8).
// O3 회사 프로필 입력도 companyStore에 반영한다(R1.1) — 홈/케이스 헤더가 이를 읽는다.
// 신규 EvidenceType을 만들지 않고 기존 'plan_created'(감사 로그 "계획 생성")를 재사용한다
// (audit.ts의 두 Record를 건드리지 않기 위함 — 코드리뷰 F1급 중복 방지 원칙과 동일).
export interface OnboardingActions {
  completeOnboarding: (role: Role, companyProfile: CompanyProfile, worker: WorkerInput) => void;
}

export function useOnboardingActions(): OnboardingActions {
  const upsert = useCaseStore((s) => s.upsert);
  const setProfile = useCompanyStore((s) => s.setProfile);
  const appendEvidence = useEvidenceStore((s) => s.append);

  return {
    completeOnboarding: (role, companyProfile, worker) => {
      setProfile(companyProfile);
      CASE_CARDS.forEach(upsert);
      upsert(workerToCard(worker, 'onboard'));
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
