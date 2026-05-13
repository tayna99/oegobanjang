import { AlertTriangle, CalendarDays, Clock, FileText, Folder, Send } from "lucide-react";

import { ActionButton } from "./ActionButton";
import { ChatPromptBox } from "./ChatPromptBox";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader, PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";

export function MobileCaseDetailScreen({ go }: { go: (step: MobileDemoStep) => void }) {
  return (
    <div className="mobile-demo-screen">
      <BrandHeader />
      <PageTitle back onBack={() => go("briefing")} title="서류 요청 상세" />
      <div className="mobile-demo-scroll">
        <MobileCard className="mobile-demo-profile">
          <span className="mobile-demo-round-icon large">
            <Folder aria-hidden="true" />
          </span>
          <div>
            <h2>{demoTask.worker.displayName}</h2>
            <p>
              {demoTask.worker.nationality} · <strong>{demoTask.worker.visaType}</strong>
            </p>
            <p>
              {demoTask.worker.worksite} {demoTask.worker.line}
            </p>
          </div>
          <div className="mobile-demo-mini-grid">
            <MiniStatus icon={<CalendarDays />} label="체류기간 만료" value={`D-${demoTask.dDay}`} />
            <MiniStatus icon={<AlertTriangle />} label="누락 서류" value={`${demoTask.missingDocuments.length}건`} />
            <MiniStatus blue icon={<Send />} label="발송 상태" value="승인 후 발송" />
          </div>
        </MobileCard>

        <h2 className="mobile-demo-section-title">AI가 확인한 내용</h2>
        <MobileCard className="mobile-demo-list">
          <InfoRow icon={<CalendarDays />} label="체류만료일" value={demoTask.expiryDate} />
          {demoTask.missingDocuments.map((document) => (
            <InfoRow chevron icon={<AlertTriangle />} key={document} label={`${document} 누락`} />
          ))}
          <InfoRow chevron icon={<Clock />} label={demoTask.previousRecord} />
        </MobileCard>

        <h2 className="mobile-demo-section-title">이 케이스에 대해 물어보기</h2>
        <ChatPromptBox
          compact
          placeholder="왜 우선 확인이야?"
          prompts={["무슨 서류가 빠졌어?", "전에 요청했어?", "검토 자료 만들 수 있어?"]}
        />

        <div className="mobile-demo-action-grid">
          <ActionButton data-testid="mobile-detail-draft" kind="outline" onClick={() => go("draft")}>
            <FileText aria-hidden="true" />
            초안 보기
          </ActionButton>
          <ActionButton data-testid="mobile-detail-approve" onClick={() => go("process")}>
            <Send aria-hidden="true" />
            대표 승인 요청
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

function MiniStatus({
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
    <div className="mobile-demo-mini-status" data-blue={blue ? "true" : undefined}>
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function InfoRow({
  chevron,
  icon,
  label,
  value,
}: {
  chevron?: boolean;
  icon: React.ReactNode;
  label: string;
  value?: string;
}) {
  return (
    <div className="mobile-demo-info-row">
      <span>{icon}</span>
      <p>{label}</p>
      {value ? <strong>{value}</strong> : null}
      {chevron ? <i>›</i> : null}
    </div>
  );
}
