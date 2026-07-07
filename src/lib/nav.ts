import { useNavigate } from 'react-router-dom';
import type { NavigateOptions } from 'react-router-dom';
import { ROUTES } from './routes';

// 화면 이동 헬퍼 — rules/frontend.md "문자열 경로 하드코딩 금지, nav.toCase(id) 사용".
export function useNav() {
  const navigate = useNavigate();
  return {
    toHome: () => navigate(ROUTES.home),
    toCases: (filter?: string) => navigate(ROUTES.cases(filter)),
    toCase: (caseId: string, options?: NavigateOptions) => navigate(ROUTES.case(caseId), options),
    toDraft: (caseId: string) => navigate(ROUTES.caseDraft(caseId)),
    toApprove: (caseId: string) => navigate(ROUTES.caseApprove(caseId)),
    toRun: (runId: string) => navigate(ROUTES.run(runId)),
    toMessages: () => navigate(ROUTES.messages),
    toThread: (threadId: string) => navigate(ROUTES.thread(threadId)),
    toEvidence: (ref?: string) => navigate(ROUTES.evidence(ref)),
    toPackage: (packageId: string) => navigate(ROUTES.package(packageId)),
    toDone: (options?: NavigateOptions) => navigate(ROUTES.done, options),
    toOnboardingWorkers: () => navigate(ROUTES.onboardingWorkers),
  };
}