import { PcOnlyNotice } from '@/components/PcOnlyNotice';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { DocScanWorkbench } from './DocScanWorkbench';

// 서류 스캔 분류(감사 §2) 컨테이너 — CsvUploadPage/WorkerDataPage와 동일하게 PC 전용(useIsDesktop 분기).
export function CasesScanPage() {
  const isDesktop = useIsDesktop();
  const nav = useNav();

  if (!isDesktop) {
    return <PcOnlyNotice title="서류 스캔 분류는 PC에서 이용해 주세요" onBack={() => nav.toCasesWorkers()} />;
  }

  return <DocScanWorkbench onCancel={() => nav.toCasesWorkers()} />;
}
