import { PcOnlyNotice } from '@/components/PcOnlyNotice';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { CsvUploadWorkbench } from './CsvUploadWorkbench';

// CSV 일괄 등록(4.4, PC 전용·통합설계 D6) 컨테이너 — useIsDesktop 분기(CaseListPage와 동일 관례).
export function CsvUploadPage() {
  const isDesktop = useIsDesktop();
  const nav = useNav();

  if (!isDesktop) {
    return <PcOnlyNotice title="CSV 일괄 등록은 PC에서 이용해 주세요" onBack={() => nav.toCases()} />;
  }

  return <CsvUploadWorkbench />;
}
