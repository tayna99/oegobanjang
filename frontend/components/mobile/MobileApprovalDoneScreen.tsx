import { AlertTriangle, CalendarDays, CheckCircle2, Clock, FileText, Info, ShieldCheck } from "lucide-react";

import { ActionButton } from "./ActionButton";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader, PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";
import type { ExternalDeliveryJob } from "../../types/dailyBriefing";

export function MobileApprovalDoneScreen({
  deliveryJob = null,
  go,
}: {
  deliveryJob?: ExternalDeliveryJob | null;
  go: (step: MobileDemoStep) => void;
}) {
  const deliveryStatus = deliveryJob ? labelDeliveryStatus(deliveryJob.status) : "발송 예정 상태";

  return (
    <div className="mobile-demo-screen">
      <BrandHeader />
      <PageTitle title="승인 완료" />
      <div className="mobile-demo-scroll">
        <div className="mobile-demo-done-mark">
          <CheckCircle2 aria-hidden="true" />
        </div>

        <MobileCard className="mobile-demo-done-card">
          <span className="mobile-demo-round-icon">
            <FileText aria-hidden="true" />
          </span>
          <div>
            <h2>보내기 승인이 완료되었습니다.</h2>
            <p>{demoTask.worker.displayName}에게 보낼 서류 요청 메시지가 승인되었습니다.</p>
            <p>
              업무 기록 <strong>#{demoTask.workLogId}</strong>에 저장되었습니다.
            </p>
            <p>관리자 대시보드에도 반영됩니다.</p>
          </div>
        </MobileCard>

        <MobileCard className="mobile-demo-safe-note">
          <Info aria-hidden="true" />
          <p>데모 환경에서는 실제 발송 없이 발송 예정 상태만 표시합니다.</p>
        </MobileCard>

        <MobileCard className="mobile-demo-list">
          <DoneRow icon={<CalendarDays />} label="체류만료" value={`D-${demoTask.dDay}`} />
          <DoneRow icon={<AlertTriangle />} label="누락 서류" value={`${demoTask.missingDocuments.length}건`} />
          <DoneRow blue icon={<Clock />} label="다음 할 일" value={deliveryStatus} />
        </MobileCard>

        <div className="mobile-demo-action-grid">
          <ActionButton kind="outline">
            <FileText aria-hidden="true" />
            업무 기록 보기
          </ActionButton>
          <ActionButton onClick={() => go("briefing")}>
            <ShieldCheck aria-hidden="true" />
            브리핑으로 돌아가기
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

function labelDeliveryStatus(status: ExternalDeliveryJob["status"]) {
  if (status === "mock_dispatched") {
    return "mock 발송 경로 확인";
  }
  if (status === "pending_manual_dispatch") {
    return "담당자 수동 발송 대기";
  }
  return "발송 예정 상태";
}

function DoneRow({
  blue,
  icon,
  label,
  value,
}: {
  blue?: boolean;
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="mobile-demo-info-row">
      <span>{icon}</span>
      <p>{label}</p>
      <strong data-blue={blue ? "true" : undefined}>{value}</strong>
    </div>
  );
}
