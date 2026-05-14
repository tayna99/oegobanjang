import { AlertTriangle, CalendarDays, CheckCircle2, Clock, FileText, Info, Send, Shield } from "lucide-react";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader } from "./MobileShell";
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
      <div className="mobile-demo-scroll">
        <div className="mobile-demo-done-mark">
          <CheckCircle2 aria-hidden="true" />
        </div>

        <div
          style={{
            background: "#F0FDF4",
            border: "1px solid rgba(16,185,129,0.3)",
            borderRadius: 16,
            margin: "0 14px 12px",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "16px 16px 14px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 999,
                  background: "rgba(16,185,129,0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                }}
              >
                ✓
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 13.5, fontWeight: 700, color: "#006E25" }}>
                  보내기 승인이 완료되었습니다.
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "#059669", marginTop: 1 }}>
                  처리 완료 · 판단 기록에 저장됨
                </p>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: 13, color: "var(--semantic-label-neutral)", lineHeight: 1.55 }}>
              {demoTask.worker.displayName}에게 보낼 서류 요청 메시지가 승인되었습니다.{" "}
              업무 기록 <strong>#{demoTask.workLogId}</strong>에 저장되었습니다.
            </p>
          </div>
        </div>

        <MobileCard className="mobile-demo-list">
          <DoneRow icon={<CalendarDays />} label="체류만료" value={`D-${demoTask.dDay}`} />
          <DoneRow icon={<AlertTriangle />} label="누락 서류" value={`${demoTask.missingDocuments.length}건`} />
          <DoneRow blue icon={<Clock />} label="다음 할 일" value={deliveryStatus} />
        </MobileCard>

        <MobileCard className="mobile-demo-safe-note">
          <Info aria-hidden="true" />
          <p>데모 환경에서는 실제 발송 없이 발송 예정 상태만 표시합니다.</p>
        </MobileCard>

        <div className="mobile-demo-approval-actions" style={{ margin: "0 0 8px" }}>
          <button
            className="mobile-demo-approve-btn"
            style={{
              background: "var(--semantic-fill-alternative)",
              color: "var(--semantic-label-normal)",
              border: "1px solid var(--semantic-line-normal-alternative)",
            }}
            type="button"
          >
            <FileText size={13} aria-hidden="true" />
            업무 기록 보기
          </button>
          <button className="mobile-demo-approve-btn" onClick={() => go("briefing")} type="button">
            <Send size={13} aria-hidden="true" />
            브리핑으로 돌아가기
          </button>
        </div>
        <div className="mobile-demo-safety-strip" style={{ justifyContent: "center" }}>
          <Shield size={11} aria-hidden="true" />
          승인 전에는 외부로 발송되지 않습니다
        </div>
      </div>
    </div>
  );
}

function labelDeliveryStatus(status: ExternalDeliveryJob["status"]) {
  if (status === "mock_dispatched") return "mock 발송 경로 확인";
  if (status === "pending_manual_dispatch") return "담당자 수동 발송 대기";
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
