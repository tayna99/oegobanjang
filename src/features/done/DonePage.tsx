import { useLocation } from 'react-router-dom';
import { Chip } from '@/components/Chip';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { useNav } from '@/lib/nav';

interface DoneLocationState {
  caseTitle?: string;
  evidenceRef?: string;
}

export function DonePage() {
  const nav = useNav();
  const location = useLocation();
  const state = (location.state ?? {}) as DoneLocationState;

  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-heading2 font-semibold text-ink">발송 승인 완료</h2>
        <Chip tone="positive">승인 기록됨</Chip>
      </div>

      <Card>
        <p className="text-body2 leading-relaxed text-ink">
          {state.caseTitle ?? '요청 건'}의 사람 승인 결정이 저장되었습니다.
        </p>
        {state.evidenceRef && <p className="mt-2 text-label1 font-semibold text-primary">판단 기록 {state.evidenceRef}</p>}
      </Card>

      <p className="mt-4 rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
        승인 전에는 외부 발송이 차단됩니다.
      </p>
      <p className="mt-3 text-body2 leading-relaxed text-muted">
        이 화면은 승인 완료 상태만 표시합니다. 실제 카톡, 문자, 정부 포털 제출은 실행하지 않습니다.
      </p>

      <Button variant="primary" className="mt-5 w-full" onClick={() => nav.toHome()}>
        오늘 브리핑으로
      </Button>
    </div>
  );
}
