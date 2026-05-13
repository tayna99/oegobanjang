import { AlertTriangle, CalendarDays, Clock, FileText, Folder, Megaphone, Pencil, Send } from "lucide-react";

import { ActionButton } from "./ActionButton";
import { ChatPromptBox } from "./ChatPromptBox";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader, PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";
import { StatusBadge } from "./StatusBadge";

export function MobileBriefingScreen({
  busyAction = null,
  go,
  onRequestRevision,
  reviewMessage,
}: {
  busyAction?: "approve" | "revision" | null;
  go: (step: MobileDemoStep) => void;
  onRequestRevision?: () => void | Promise<void>;
  reviewMessage?: string | null;
}) {
  return (
    <div className="mobile-demo-screen">
      <BrandHeader />
      <PageTitle date="2026.05.21" title="오늘 브리핑" />
      <div className="mobile-demo-scroll">
        <MobileCard className="mobile-demo-notice">
          <span>
            <Megaphone aria-hidden="true" />
          </span>
          <p>
            대표님, 오늘 확인이 필요한
            <br />
            외국인 고용 업무가 <strong>3건</strong> 있습니다.
          </p>
        </MobileCard>

        <MobileCard className="mobile-demo-main-task">
          <div className="mobile-demo-task-head">
            <span className="mobile-demo-round-icon">
              <Folder aria-hidden="true" />
            </span>
            <button data-testid="mobile-open-detail" onClick={() => go("detail")} type="button">
              {demoTask.worker.displayName} 체류기간 연장 서류 요청
            </button>
            <StatusBadge tone="danger">HIGH</StatusBadge>
          </div>
          <div className="mobile-demo-task-facts">
            <StatusLine icon={<CalendarDays />} label="체류만료" value={`D-${demoTask.dDay}`} />
            <StatusLine icon={<AlertTriangle />} label="누락 서류" value={`${demoTask.missingDocuments.length}건`} />
          </div>
          <p className="mobile-demo-copy">
            AI가 베트남어 요청 메시지를 준비했습니다.
            <br />
            승인 후에는 발송 예정 상태로 기록됩니다.
          </p>
          {reviewMessage ? (
            <div className="mobile-demo-safe-note">
              <AlertTriangle aria-hidden="true" />
              <p>{reviewMessage}</p>
            </div>
          ) : null}
          <div className="mobile-demo-divider" />
          <div className="mobile-demo-action-grid three">
            <ActionButton data-testid="mobile-briefing-draft" kind="outline" onClick={() => go("draft")}>
              <FileText aria-hidden="true" />
              초안 보기
            </ActionButton>
            <ActionButton data-testid="mobile-briefing-revision" kind="teal" onClick={onRequestRevision}>
              <Pencil aria-hidden="true" />
              {busyAction === "revision" ? "요청 중" : "수정 요청"}
            </ActionButton>
            <ActionButton data-testid="mobile-briefing-approve" onClick={() => go("process")}>
              <Send aria-hidden="true" />
              보내기 승인
            </ActionButton>
          </div>
        </MobileCard>

        <div className="mobile-demo-summary-grid">
          <SummaryCard color="orange" count="2건" icon={<FileText />} label="서류 보완 필요" />
          <SummaryCard color="blue" count="1건" icon={<Clock />} label="승인 대기" />
        </div>

        <ChatPromptBox
          placeholder="이 메시지 조금 더 정중하게 바꿔줘"
          prompts={["짧게 줄여줘", "더 정중하게", "응답 늦으면 어떻게 해?"]}
        />
      </div>
    </div>
  );
}

function StatusLine({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="mobile-demo-status-line">
      <span>{icon}</span>
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  );
}

function SummaryCard({
  color,
  count,
  icon,
  label,
}: {
  color: "blue" | "orange";
  count: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <MobileCard className="mobile-demo-summary" data-color={color}>
      <span>{icon}</span>
      <p>{label}</p>
      <strong>{count}</strong>
    </MobileCard>
  );
}
