import { AlertTriangle, CalendarDays, Clock, FileText, Folder, HelpCircle, Info, Pencil, Send, ThumbsUp } from "lucide-react";

import { ActionButton } from "./ActionButton";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";

export function MobileDraftScreen({
  backTo = "process",
  busyAction = null,
  go,
  onApprove,
  onRequestRevision,
  reviewMessage,
}: {
  backTo?: MobileDemoStep;
  busyAction?: "approve" | "revision" | null;
  go: (step: MobileDemoStep) => void;
  onApprove?: () => void | Promise<void>;
  onRequestRevision?: () => void | Promise<void>;
  reviewMessage?: string | null;
}) {
  return (
    <div className="mobile-demo-screen">
      <PageTitle back onBack={() => go(backTo)} title="메시지 초안" />
      <div className="mobile-demo-scroll">
        <MobileCard className="mobile-demo-draft-worker">
          <span className="mobile-demo-round-icon">
            <Folder aria-hidden="true" />
          </span>
          <div>
            <h2>{demoTask.worker.displayName}</h2>
            <p>
              <CalendarDays aria-hidden="true" /> 체류만료 <strong>D-{demoTask.dDay}</strong>
              <AlertTriangle aria-hidden="true" /> 누락 서류 <strong>{demoTask.missingDocuments.length}건</strong>
            </p>
          </div>
        </MobileCard>

        <MobileCard className="mobile-demo-message">
          <LanguageBlock label="VN" text={demoTask.draft.vi} />
          <div className="mobile-demo-divider" />
          <LanguageBlock label="KR" text={demoTask.draft.ko} tone="blue" />
        </MobileCard>

        <h2 className="mobile-demo-section-title">예상 응답</h2>
        <ExpectedCard desc="반영 후보 생성 후 담당자 확인" icon={<ThumbsUp />} label="긍정 응답" tone="teal" />
        <ExpectedCard desc="제출 형식 안내" icon={<HelpCircle />} label="추가 질문" tone="blue" />
        <ExpectedCard desc="2일 뒤 리마인드 제안" icon={<Clock />} label="응답 지연" tone="orange" />

        {reviewMessage ? (
          <MobileCard className="mobile-demo-safe-note">
            <Info aria-hidden="true" />
            <p>{reviewMessage}</p>
          </MobileCard>
        ) : null}

        <div className="mobile-demo-action-grid">
          <ActionButton data-testid="mobile-draft-revision" kind="teal" onClick={onRequestRevision}>
            <Pencil aria-hidden="true" />
            {busyAction === "revision" ? "요청 중" : "수정 요청"}
          </ActionButton>
          <ActionButton data-testid="mobile-draft-approve" onClick={onApprove ?? (() => go("done"))}>
            <Send aria-hidden="true" />
            {busyAction === "approve" ? "승인 중" : "보내기 승인"}
          </ActionButton>
        </div>

        <MobileCard className="mobile-demo-log-note">
          <Info aria-hidden="true" />
          <p>
            승인 시 업무 기록 <strong>#{demoTask.workLogId}</strong>에 저장됩니다.
          </p>
        </MobileCard>
      </div>
    </div>
  );
}

function LanguageBlock({ label, text, tone }: { label: string; text: string; tone?: "blue" }) {
  return (
    <div className="mobile-demo-language">
      <span data-tone={tone}>{label}</span>
      <p>{text}</p>
    </div>
  );
}

function ExpectedCard({
  desc,
  icon,
  label,
  tone,
}: {
  desc: string;
  icon: React.ReactNode;
  label: string;
  tone: "blue" | "orange" | "teal";
}) {
  return (
    <MobileCard className="mobile-demo-expected">
      <span data-tone={tone}>{icon}</span>
      <div>
        <strong>{label}</strong>
        <p>{desc}</p>
      </div>
      <i>›</i>
    </MobileCard>
  );
}
