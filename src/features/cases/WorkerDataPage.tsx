import { PcOnlyNotice } from '@/components/PcOnlyNotice';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { WorkerDataWorkbench } from './WorkerDataWorkbench';

// 근로자 데이터 관리(PC 4b) 컨테이너 — CSV 업로드와 동일하게 PC 전용(useIsDesktop 분기).
export function WorkerDataPage() {
  const isDesktop = useIsDesktop();
  const nav = useNav();

  if (!isDesktop) {
    return <PcOnlyNotice title="근로자 데이터 관리는 PC에서 이용해 주세요" onBack={() => nav.toCases()} />;
  }

  return <WorkerDataWorkbench />;
}
