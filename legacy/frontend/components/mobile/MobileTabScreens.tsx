import { FileText, MessageSquare, ShieldCheck, UserRoundCheck } from "lucide-react";

import type { MobileDemoStep } from "./demoTask";
import { demoTask } from "./demoTask";
import { MobileCard } from "./MobileCard";
import { BrandHeader, PageTitle } from "./MobileShell";
import { StatusBadge } from "./StatusBadge";

type MobileTabScreensProps = {
  go: (step: MobileDemoStep) => void;
  tab: "workers" | "contact" | "cases" | "more";
};

export function MobileTabScreen({ go, tab }: MobileTabScreensProps) {
  if (tab === "workers") return <MobileWorkersTab go={go} />;
  if (tab === "contact") return <MobileContactTab go={go} />;
  if (tab === "cases") return <MobileCasesTab go={go} />;
  return <MobileMoreTab />;
}

function MobileWorkersTab({ go }: { go: (step: MobileDemoStep) => void }) {
  return (
    <div className="mobile-demo-screen">
      <div className="mobile-demo-scroll">
        <BrandHeader noticeCount={2} />
        <PageTitle title="근로자" date="6명" />
        <MobileCard className="mobile-demo-profile">
          <span className="mobile-demo-round-icon large">V</span>
          <h2>{demoTask.worker.displayName}</h2>
          <p>{demoTask.worker.nationality} · {demoTask.worker.visaType} · {demoTask.worker.worksite}</p>
          <div className="mobile-demo-mini-grid">
            <Mini label="체류만료" value={`D-${demoTask.dDay}`} tone="orange" />
            <Mini label="누락서류" value={`${demoTask.missingDocuments.length}건`} tone="blue" />
          </div>
          <button className="mobile-demo-approve-btn" onClick={() => go("detail")} type="button">
            상세 보기
          </button>
        </MobileCard>
        <MobileCard className="mobile-demo-list">
          <InfoRow title="Bayar M." body="체류만료 초과 · 행정사 검토 자료 필요" />
          <InfoRow title="Tran T.H." body="계약 종료 응답 도착 · 담당자 확인 필요" />
        </MobileCard>
      </div>
    </div>
  );
}

function MobileContactTab({ go }: { go: (step: MobileDemoStep) => void }) {
  return (
    <div className="mobile-demo-screen">
      <div className="mobile-demo-scroll">
        <BrandHeader noticeCount={2} />
        <PageTitle title="컨택" date="승인 대기 2건" />
        <MobileCard className="mobile-demo-approval-card">
          <div className="mobile-demo-approval-meta">
            <MessageSquare size={18} aria-hidden="true" />
            <StatusBadge tone="muted">초안</StatusBadge>
          </div>
          <p className="mobile-demo-approval-title-text">{demoTask.worker.displayName} 서류 요청 메시지</p>
          <p className="mobile-demo-approval-body">Zalo 발송 전 담당자 승인 대기 중입니다.</p>
          <div className="mobile-demo-approval-actions">
            <button className="mobile-demo-approve-btn" onClick={() => go("draft")} type="button">
              초안 보기
            </button>
          </div>
        </MobileCard>
        <MobileCard className="mobile-demo-list">
          <InfoRow title="Tran T.H." body="응답 도착 · 계약 종료 확인 요약" />
          <InfoRow title="Mohammad I." body="SMS 초안 · 재계약 서류 안내" />
        </MobileCard>
      </div>
    </div>
  );
}

function MobileCasesTab({ go }: { go: (step: MobileDemoStep) => void }) {
  return (
    <div className="mobile-demo-screen">
      <div className="mobile-demo-scroll">
        <BrandHeader noticeCount={2} />
        <PageTitle title="케이스" date="확인 필요 7건" />
        <MobileCard className="mobile-demo-approval-card">
          <div className="mobile-demo-approval-meta">
            <FileText size={18} aria-hidden="true" />
            <StatusBadge tone="danger">우선 확인</StatusBadge>
            <span className="mobile-demo-dday" data-urgent="true">D-{demoTask.dDay}</span>
          </div>
          <button className="mobile-demo-approval-title" onClick={() => go("detail")} type="button">
            {demoTask.worker.displayName} 체류기간 연장 서류 요청
          </button>
          <p className="mobile-demo-approval-body">누락 서류 2건과 이전 요청 이력을 확인해야 합니다.</p>
        </MobileCard>
        <MobileCard className="mobile-demo-list">
          <InfoRow title="Bayar M." body="즉시 확인 · 체류만료 초과" />
          <InfoRow title="사업장 전체" body="우선 확인 · 고용변동 신고기한" />
        </MobileCard>
      </div>
    </div>
  );
}

function MobileMoreTab() {
  return (
    <div className="mobile-demo-screen">
      <div className="mobile-demo-scroll">
        <BrandHeader noticeCount={2} />
        <PageTitle title="더보기" date="운영 메뉴" />
        <MobileCard className="mobile-demo-list">
          <InfoRow title="승인 기록" body="승인 완료, 수정 요청, 발송 예정 상태 확인" />
          <InfoRow title="판단 기록" body={`업무 기록 #${demoTask.workLogId}와 근거 이벤트 확인`} />
          <InfoRow title="CSV 운영" body="PC 관리자 화면에서 원천 데이터를 검증합니다." />
        </MobileCard>
        <MobileCard className="mobile-demo-safe-note">
          <ShieldCheck size={18} aria-hidden="true" />
          <p>모바일 화면에서도 메시지 발송과 외부 전달은 자동 실행하지 않습니다.</p>
        </MobileCard>
      </div>
    </div>
  );
}

function Mini({ label, value, tone }: { label: string; value: string; tone: "blue" | "orange" }) {
  return (
    <div className="mobile-demo-mini-status" data-blue={tone === "blue" ? "true" : undefined}>
      <UserRoundCheck size={18} aria-hidden="true" />
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function InfoRow({ title, body }: { title: string; body: string }) {
  return (
    <div className="mobile-demo-info-row">
      <span />
      <p>
        <strong>{title}</strong>
        <i>{body}</i>
      </p>
    </div>
  );
}
