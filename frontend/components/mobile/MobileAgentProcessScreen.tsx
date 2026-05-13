import { CircleCheck, FileText, MoreHorizontal, Pencil, Send, ShieldCheck, Sparkles } from "lucide-react";

import { ActionButton } from "./ActionButton";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader, PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";

const steps = [
  ["1", "근로자 프로필 확인 완료", `${demoTask.worker.name} · ${demoTask.worker.nationality} · ${demoTask.worker.visaType} · ${demoTask.worker.contactChannel}`, true],
  ["2", "이전 대화 기록 확인 완료", `3일 전 ${demoTask.missingDocuments[0]} 요청 이력 있음`, true],
  ["3", "메시지 초안 생성 완료", "베트남어 원문 + 한국어 번역 생성", true],
  ["4", "발송 전 승인 대기", "대표님 승인 후 근로자에게 발송 예정 상태로 기록됩니다", false],
] as const;

export function MobileAgentProcessScreen({
  busyAction = null,
  go,
  onApprove,
  onRequestRevision,
}: {
  busyAction?: "approve" | "revision" | null;
  go: (step: MobileDemoStep) => void;
  onApprove?: () => void | Promise<void>;
  onRequestRevision?: () => void | Promise<void>;
}) {
  return (
    <div className="mobile-demo-screen">
      <BrandHeader />
      <PageTitle date="2026.05.21" title="Multilingual Contact Agent" />
      <div className="mobile-demo-scroll">
        <MobileCard className="mobile-demo-notice">
          <span>
            <Sparkles aria-hidden="true" />
          </span>
          <p>AI가 승인 전까지 필요한 작업을 정리했습니다.</p>
        </MobileCard>

        <MobileCard className="mobile-demo-process">
          {steps.map(([no, title, desc, done]) => (
            <div className="mobile-demo-step" key={no}>
              <span className={done ? "done" : ""}>{no}</span>
              <i className={done ? "done" : ""}>{done ? <CircleCheck /> : <MoreHorizontal />}</i>
              <div>
                <strong>{title}</strong>
                <p>{desc}</p>
              </div>
            </div>
          ))}
        </MobileCard>

        <MobileCard className="mobile-demo-safe-note">
          <ShieldCheck aria-hidden="true" />
          <p>
            승인 전에는 외부 발송을 실행하지 않습니다. 승인 결과는 판단 기록{" "}
            <strong>#{demoTask.workLogId}</strong>에 남습니다.
          </p>
        </MobileCard>

        <MobileCard className="mobile-demo-message">
          <div className="mobile-demo-language">
            <span>VN</span>
            <p>{demoTask.draft.politeVi}</p>
          </div>
          <div className="mobile-demo-divider" />
          <div className="mobile-demo-language">
            <span data-tone="blue">KR</span>
            <p>{demoTask.draft.politeKo}</p>
          </div>
        </MobileCard>

        <div className="mobile-demo-action-grid three">
          <ActionButton kind="outline" onClick={() => go("draft")}>
            <FileText aria-hidden="true" />
            초안 확인
          </ActionButton>
          <ActionButton kind="teal" onClick={onRequestRevision}>
            <Pencil aria-hidden="true" />
            {busyAction === "revision" ? "요청 중" : "수정 요청"}
          </ActionButton>
          <ActionButton onClick={onApprove ?? (() => go("done"))}>
            <Send aria-hidden="true" />
            {busyAction === "approve" ? "승인 중" : "최종 승인"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
