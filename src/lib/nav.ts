import { useNavigate } from 'react-router-dom';
import type { NavigateOptions } from 'react-router-dom';
import { ROUTES } from './routes';

// 화면 이동 헬퍼 — rules/frontend.md "문자열 경로 하드코딩 금지, nav.toCase(id) 사용".
export function useNav() {
  const navigate = useNavigate();
  return {
    toHome: () => navigate(ROUTES.home),
    toCases: (filter?: string) => navigate(ROUTES.cases(filter)),
    toCasesImport: () => navigate(ROUTES.casesImport),
    toCasesWorkers: () => navigate(ROUTES.casesWorkers),
    toCasesDispatch: () => navigate(ROUTES.casesDispatch),
    toCase: (caseId: string, options?: NavigateOptions) => navigate(ROUTES.case(caseId), options),
    toDraft: (caseId: string) => navigate(ROUTES.caseDraft(caseId)),
    toApprove: (caseId: string) => navigate(ROUTES.caseApprove(caseId)),
    toCaseHistory: (caseId: string) => navigate(ROUTES.caseHistory(caseId)),
    toRun: (runId: string) => navigate(ROUTES.run(runId)),
    // R4.1 — CommandBar real 모드 전용. message는 location.state로 전달(runId를 미리
    // 발급받지 않음 — 백엔드가 SSE 첫 프레임으로 run_id를 만든다).
    toLiveRun: (message: string) => navigate(ROUTES.runLive, { state: { message } }),
    toMessages: () => navigate(ROUTES.messages),
    toThread: (threadId: string) => navigate(ROUTES.thread(threadId)),
    toEvidence: (ref?: string) => navigate(ROUTES.evidence(ref)),
    toPackage: (packageId: string) => navigate(ROUTES.package(packageId)),
    toDone: (options?: NavigateOptions) => navigate(ROUTES.done, options),
    toOnboarding: () => navigate(ROUTES.onboarding),
    toExpertDashboard: (expertId: string) => navigate(ROUTES.expertDashboard(expertId)),
    toExpertPackage: (expertId: string, packageId: string) => navigate(ROUTES.expertPackage(expertId, packageId)),
    toSettings: () => navigate(ROUTES.settings),
    toSettingsMembers: () => navigate(ROUTES.settingsMembers),
    toSettingsDelegation: () => navigate(ROUTES.settingsDelegation),
  };
}