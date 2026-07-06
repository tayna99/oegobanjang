import { AlertTriangle, CalendarDays, Clock, FileText, Send, Shield } from "lucide-react";
import { ActionButton } from "./ActionButton";
import { ChatPromptBox } from "./ChatPromptBox";
import { demoTask, type MobileDemoStep } from "./demoTask";
import { BrandHeader } from "./MobileShell";
import { MobileCard } from "./MobileCard";

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
  const pendingCount = 3;

  return (
    <div className="mobile-demo-screen">
      <BrandHeader noticeCount={pendingCount} />
      <div className="mobile-demo-scroll">
        <div className="mobile-demo-briefing-header">
          <div>
            <h2 className="mobile-demo-briefing-title">오늘 브리핑</h2>
            <p className="mobile-demo-briefing-date">2026년 5월 21일 (목)</p>
          </div>
          <div className="mobile-demo-company-chip">
            <span>한</span>
            한별제조
          </div>
        </div>

        <div className="mobile-demo-ai-bubble">
          <div className="mobile-demo-ai-bubble-header">
            <span className="mobile-demo-ai-mark">반</span>
            <strong>AI 반장</strong>
            <span className="mobile-demo-ai-time">· 오늘 08:00</span>
          </div>
          <p>
            대표님, 오늘 확인이 필요한 외국인 고용 업무가{" "}
            <strong style={{ color: "#1B3FA0" }}>{pendingCount}건</strong> 있습니다.
            각 카드를 확인하고 승인해 주세요.
          </p>
        </div>

        <div className="mobile-demo-section-label">
          승인 대기 업무
          <span className="mobile-demo-section-badge">{pendingCount}건</span>
        </div>

        <div className="mobile-demo-approval-card">
          <div className="mobile-demo-approval-card-top" />
          <div style={{ padding: "14px 16px" }}>
            <div className="mobile-demo-approval-meta">
              <span className="mobile-demo-flag">🇻🇳</span>
              <span className="mobile-demo-status-chip" data-tone="orange">승인 필요</span>
              <span className="mobile-demo-dday" data-urgent="true">D-{demoTask.dDay}</span>
            </div>
            <button
              className="mobile-demo-approval-title"
              data-testid="mobile-open-detail"
              onClick={() => go("detail")}
              type="button"
            >
              {demoTask.worker.displayName} 체류기간 연장 서류 요청
            </button>
            <p className="mobile-demo-approval-highlight" data-tone="orange">
              서류 {demoTask.missingDocuments.length}건 누락 · 만료 임박
            </p>
            <p className="mobile-demo-approval-body">
              AI가 베트남어 요청 메시지를 준비했습니다. 승인 후 발송 예정 상태로 기록됩니다.
            </p>
          </div>
          <div className="mobile-demo-approval-actions">
            <ActionButton data-testid="mobile-briefing-draft" kind="outline" onClick={() => go("draft")}>
              <FileText aria-hidden="true" />
              초안 보기
            </ActionButton>
            <button
              className="mobile-demo-approve-btn"
              data-testid="mobile-briefing-approve"
              onClick={() => go("process")}
              type="button"
            >
              <Send size={13} aria-hidden="true" />
              {busyAction === "approve" ? "승인 중" : "승인하기"}
            </button>
          </div>
          <div className="mobile-demo-safety-strip">
            <Shield size={11} aria-hidden="true" />
            승인 전에는 외부로 발송되지 않습니다
          </div>
        </div>

        <div className="mobile-demo-approval-card">
          <div className="mobile-demo-approval-card-top" style={{ background: "#3B82F6" }} />
          <div style={{ padding: "14px 16px" }}>
            <div className="mobile-demo-approval-meta">
              <span className="mobile-demo-flag">🇲🇳</span>
              <span className="mobile-demo-status-chip" data-tone="blue">검토 필요</span>
            </div>
            <p className="mobile-demo-approval-title-text">Bayar M. 체류 초과 — 행정사 검토 자료</p>
            <p className="mobile-demo-approval-body">
              체류기간이 D+3 초과 상태입니다. 행정사 검토용 패키지가 준비됐습니다.
            </p>
          </div>
          <div className="mobile-demo-approval-actions">
            <ActionButton kind="outline" onClick={() => go("draft")}>
              <FileText aria-hidden="true" />
              검토 자료 보기
            </ActionButton>
            <button className="mobile-demo-approve-btn" type="button">
              <Send size={13} aria-hidden="true" />
              승인하기
            </button>
          </div>
          <div className="mobile-demo-safety-strip">
            <Shield size={11} aria-hidden="true" />
            승인 전에는 외부 전달이 수행되지 않습니다
          </div>
        </div>

        <div className="mobile-demo-summary-grid">
          <MobileCard className="mobile-demo-summary" data-color="orange">
            <span><FileText /></span>
            <p>서류 보완 필요</p>
            <strong>2건</strong>
          </MobileCard>
          <MobileCard className="mobile-demo-summary" data-color="blue">
            <span><Clock /></span>
            <p>승인 대기</p>
            <strong>1건</strong>
          </MobileCard>
        </div>

        {reviewMessage ? (
          <MobileCard className="mobile-demo-safe-note">
            <AlertTriangle aria-hidden="true" />
            <p>{reviewMessage}</p>
          </MobileCard>
        ) : null}

        <ChatPromptBox
          placeholder="이 메시지 조금 더 정중하게 바꿔줘"
          prompts={["짧게 줄여줘", "더 정중하게", "응답 늦으면 어떻게 해?"]}
        />
      </div>
    </div>
  );
}
