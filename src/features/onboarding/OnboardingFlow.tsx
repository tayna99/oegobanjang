import { useState } from 'react';
import { Button } from '@/components/Button';
import { useNav } from '@/lib/nav';
import { useOnboardingActions } from '@/lib/onboarding';
import { useRoleStore } from '@/stores/roleStore';
import type { Role } from '@/types';
import { StepPhoneAuth } from './StepPhoneAuth';
import { StepRole } from './StepRole';
import { StepCompany } from './StepCompany';
import type { CompanyFields } from './StepCompany';
import { StepFirstWorker } from './StepFirstWorker';
import type { WorkerFields, WorkerPath } from './StepFirstWorker';
import { StepBriefingLoading, StepBriefingDone } from './StepBriefingReady';

// 온보딩 O1~O5(4.1) — Shell(로그인 앱 챙) 바깥의 전체 화면 상태 머신(router.tsx 형제 라우트).
// reference/design-system/외고반장 온보딩.dc.html의 1a 인터랙티브 플로우를 그대로 이식 —
// 순차 게이트(O1 인증 없이 O2로 못 감)라 딥링크 카탈로그에 O1~O5 개별 경로를 두지 않는다.
type OnboardingStep = 'o1' | 'o2' | 'o3' | 'o4' | 'o5load' | 'o5done';
const STEP_ORDER: OnboardingStep[] = ['o1', 'o2', 'o3', 'o4', 'o5load', 'o5done'];
const PROGRESS_INDEX: Record<OnboardingStep, number> = { o1: 0, o2: 1, o3: 2, o4: 3, o5load: 4, o5done: 4 };

const DEFAULT_COMPANY_FIELDS: CompanyFields = {
  name: '그린푸드 제조',
  region: '경기 화성',
  industry: '식품 제조업',
  workerCount: '6명',
};

const DEFAULT_WORKER_FIELDS: WorkerFields = {
  name: 'Nguyen Van A',
  nationality: '베트남',
  team: '제조1팀',
  stayExpiryDate: '2026-08-09',
};

export function OnboardingFlow() {
  const nav = useNav();
  const setRole = useRoleStore((s) => s.setRole);
  const { completeOnboarding } = useOnboardingActions();

  const [step, setStep] = useState<OnboardingStep>('o1');
  const [codeConfirmed, setCodeConfirmed] = useState(false);
  const [role, setRoleLocal] = useState<Role | null>(null);
  const [companyFields, setCompanyFields] = useState(DEFAULT_COMPANY_FIELDS);
  const [workerPath, setWorkerPath] = useState<WorkerPath>('direct');
  const [workerFields, setWorkerFields] = useState(DEFAULT_WORKER_FIELDS);

  const goNext = () => setStep((s) => STEP_ORDER[Math.min(STEP_ORDER.indexOf(s) + 1, STEP_ORDER.length - 1)]);
  const goBack = () => setStep((s) => STEP_ORDER[Math.max(STEP_ORDER.indexOf(s) - 1, 0)]);

  const showBack = step === 'o2' || step === 'o3' || step === 'o4';
  const showProgress = step !== 'o5load' && step !== 'o5done';
  const showCta = step !== 'o5load';

  const canProceed =
    step === 'o1'
      ? codeConfirmed
      : step === 'o2'
        ? role !== null
        : step === 'o3'
          ? Object.values(companyFields).every((v) => v.trim().length > 0)
          : step === 'o4'
            ? workerPath !== 'direct' ||
              (workerFields.name.trim().length > 0 &&
                workerFields.nationality.trim().length > 0 &&
                workerFields.team.trim().length > 0 &&
                workerFields.stayExpiryDate.trim().length > 0)
            : true;

  const ctaLabel = step === 'o4' ? '등록하고 브리핑 만들기' : step === 'o5done' ? '오늘 브리핑 보기' : '다음';

  const onCta = () => {
    if (step === 'o2' && role) setRole(role);
    if (step === 'o4') {
      completeOnboarding(role ?? 'manager', companyFields);
      goNext(); // o4 → o5load
      return;
    }
    if (step === 'o5done') {
      nav.toHome();
      return;
    }
    goNext();
  };

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-sm flex-col bg-canvas">
      <div className="flex min-h-12 items-center gap-3 px-5 pt-8 pb-1">
        {showBack && (
          <button type="button" aria-label="뒤로" onClick={goBack} className="flex size-9 shrink-0 items-center justify-center rounded-in text-ink active:bg-surface">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M15 5L8 12L15 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
        {showProgress && (
          <div className="flex flex-1 gap-1.5" role="progressbar" aria-label="온보딩 진행률" aria-valuenow={PROGRESS_INDEX[step] + 1} aria-valuemin={1} aria-valuemax={5}>
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} className={`h-1 flex-1 rounded-chip ${i <= PROGRESS_INDEX[step] ? 'bg-primary' : 'bg-track'}`} />
            ))}
          </div>
        )}
      </div>

      <main className="flex flex-1 flex-col overflow-y-auto px-5 pt-2 pb-4">
        {step === 'o1' && <StepPhoneAuth onCodeConfirmedChange={setCodeConfirmed} />}
        {step === 'o2' && <StepRole role={role} onRoleChange={setRoleLocal} />}
        {step === 'o3' && <StepCompany fields={companyFields} onFieldsChange={setCompanyFields} />}
        {step === 'o4' && (
          <StepFirstWorker
            path={workerPath}
            onPathChange={setWorkerPath}
            fields={workerFields}
            onFieldsChange={setWorkerFields}
          />
        )}
        {step === 'o5load' && <StepBriefingLoading onComplete={goNext} />}
        {step === 'o5done' && <StepBriefingDone />}
      </main>

      {showCta && (
        <div className="border-t border-hairline px-5 pt-3 pb-10">
          <Button variant="primary" className="w-full" disabled={!canProceed} onClick={onCta}>
            {ctaLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
