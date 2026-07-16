import { Button } from '@/components/Button';

// PC 전용 화면(CSV 업로드·근로자 데이터 관리 등)의 모바일 분기 안내 — 그린필드
// (src/에 원래 선례 없음, 온보딩 O4의 "PC 권장" 카드와 동일 톤). useIsDesktop()이
// false일 때 각 컨테이너가 이 컴포넌트로 대체 렌더한다.
export interface PcOnlyNoticeProps {
  title: string;
  onBack: () => void;
  backLabel?: string;
}

export function PcOnlyNotice({ title, onBack, backLabel = '케이스로 돌아가기' }: PcOnlyNoticeProps) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="text-body1 font-semibold text-ink">{title}</p>
      <p className="text-body2 text-muted">이 화면은 큰 화면에 최적화되어 있습니다.</p>
      <Button variant="outline" onClick={onBack}>
        {backLabel}
      </Button>
    </div>
  );
}
