import { CheckCircle2, FileText, MoreHorizontal, Shield, Sparkles } from "lucide-react";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader, PageTitle } from "./MobileShell";
import { MobileCard } from "./MobileCard";

const steps = [
  ["1", "근로자 정보 확인 완료", `${demoTask.worker.displayName} · ${demoTask.worker.nationality} · ${demoTask.worker.visaType}`, true],
  ["2", "이전 기록 확인 완료", demoTask.previousRecord, true],
  ["3", "메시지 초안 생성 완료", "베트남어 원문 + 한국어 번역 생성", true],
  ["4", "발송 전 승인 대기", "대표님 승인 후 발송됩니다", false],
] as const;

export function MobileAgentProcessScreen({ go }: { go: (step: MobileDemoStep) => void }) {
  return (
    <div className="mobile-demo-screen">
      <BrandHeader />
      <PageTitle date="2026.05.21" title="AI 처리 과정" />
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
              <i className={done ? "done" : ""}>{done ? <CheckCircle2 /> : <MoreHorizontal />}</i>
              <div>
                <strong>{title}</strong>
                <p>{desc}</p>
              </div>
            </div>
          ))}
        </MobileCard>

        <div className="mobile-demo-safety-strip" style={{ justifyContent: "center", margin: "0 0 8px" }}>
          <Shield size={11} aria-hidden="true" />
          AI는 실제 전달을 자동으로 실행하지 않습니다.
        </div>

        <div className="mobile-demo-approval-actions" style={{ margin: "0 0 8px" }}>
          <button
            className="mobile-demo-approve-btn"
            data-testid="mobile-process-draft"
            onClick={() => go("draft")}
            type="button"
          >
            <FileText size={13} aria-hidden="true" />
            초안 확인하기
          </button>
        </div>
      </div>
    </div>
  );
}
