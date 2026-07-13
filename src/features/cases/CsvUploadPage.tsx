import { Button } from '@/components/Button';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { CsvUploadWorkbench } from './CsvUploadWorkbench';

// CSV 일괄 등록(4.4, PC 전용·통합설계 D6) 컨테이너 — useIsDesktop 분기(CaseListPage와
// 동일 관례). 이 화면만 PC 전용이라 모바일 분기는 다른 화면(항상 모바일 트리 보유)과
// 달리 PC 유도 안내만 보여준다(그린필드 — src/에 선례 없음, 온보딩 O4의 "PC 권장" 카드와
// 동일 톤으로 새로 만듦).
export function CsvUploadPage() {
  const isDesktop = useIsDesktop();
  const nav = useNav();

  if (!isDesktop) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-body1 font-semibold text-ink">CSV 일괄 등록은 PC에서 이용해 주세요</p>
        <p className="text-body2 text-muted">여러 근로자를 한 번에 등록하는 화면은 큰 화면에 최적화되어 있습니다.</p>
        <Button variant="outline" onClick={() => nav.toCases()}>
          케이스로 돌아가기
        </Button>
      </div>
    );
  }

  return <CsvUploadWorkbench />;
}
