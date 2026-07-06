"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, FileText, Loader2, ShieldCheck } from "lucide-react";

import { Badge, Button, cn } from "./ui";
import styles from "./PcShell.module.css";

const COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001";

type WorkerInfo = {
  id: string;
  name: string;
  full_name?: string;
  nationality?: string;
  visa_type?: string;
  visa_expires_at?: string;
  contract_starts_at?: string;
  contract_ends_at?: string;
  language_code?: string;
};

type AgentResult = {
  text: string;
  approvalRequired: boolean;
};

type WorkerDetailPageProps = {
  workerId: string;
};

function calcDday(dateStr?: string): string {
  if (!dateStr) return "";
  const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
  if (diff > 0) return `D-${diff}`;
  if (diff === 0) return "D-Day";
  return `D+${Math.abs(diff)}`;
}

function calcTenure(startStr?: string): string {
  if (!startStr) return "";
  const months = Math.floor((Date.now() - new Date(startStr).getTime()) / (30 * 86400000));
  if (months < 12) return `${months}개월`;
  return `${Math.floor(months / 12)}년 ${months % 12}개월`;
}

export function WorkerDetailPage({ workerId }: WorkerDetailPageProps) {
  const [worker, setWorker] = useState<WorkerInfo | null>(null);
  const [loadingWorker, setLoadingWorker] = useState(true);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentResult, setAgentResult] = useState<AgentResult | null>(null);
  const [activeButton, setActiveButton] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch(`/api/v1/contact/workers?company_id=${encodeURIComponent(COMPANY_ID)}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json() as { workers: WorkerInfo[] };
        const found = data.workers.find((w) => w.id === workerId);
        setWorker(found ?? data.workers[0] ?? null);
      } finally {
        setLoadingWorker(false);
      }
    })();
  }, [workerId]);

  async function runAgent(userMessage: string, buttonLabel: string) {
    setAgentLoading(true);
    setActiveButton(buttonLabel);
    setAgentResult(null);
    try {
      const res = await fetch("/api/v1/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: userMessage,
          company_id: COMPANY_ID,
          worker_id: workerId,
          persist_result: false,
        }),
      });
      if (!res.ok) {
        setAgentResult({ text: "에이전트 호출에 실패했습니다.", approvalRequired: false });
        return;
      }
      const data = await res.json() as { final_response?: string; approval_required?: boolean };
      setAgentResult({
        text: data.final_response ?? "응답 없음",
        approvalRequired: data.approval_required ?? false,
      });
    } finally {
      setAgentLoading(false);
    }
  }

  if (loadingWorker) {
    return (
      <div className={styles.stack} style={{ alignItems: "center", paddingTop: 48 }}>
        <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} />
        <p className={styles.subtle}>근로자 정보를 불러오는 중...</p>
      </div>
    );
  }

  if (!worker) {
    return (
      <div className={styles.stack}>
        <div className={styles.pageHead}>
          <Link className={styles.pill} href="/workers">
            <ArrowLeft size={14} aria-hidden="true" />
            근로자 목록
          </Link>
          <p className={styles.subtle} style={{ marginTop: 14 }}>근로자 정보를 찾을 수 없습니다.</p>
        </div>
      </div>
    );
  }

  const visaExpiry = worker.visa_expires_at ?? "";
  const dday = calcDday(visaExpiry);
  const contractEnd = worker.contract_ends_at ?? "";
  const tenure = calcTenure(worker.contract_starts_at);
  const initials = (worker.full_name ?? worker.name ?? "?").slice(0, 2).toUpperCase();
  const displayName = worker.name ?? worker.full_name ?? "이름 없음";

  return (
    <div className={styles.stack}>
      <div className={styles.pageHead}>
        <div>
          <Link className={styles.pill} href="/workers">
            <ArrowLeft size={14} aria-hidden="true" />
            근로자 목록
          </Link>
          <h1 className={styles.headline} style={{ marginTop: 14 }}>{displayName}</h1>
          <p className={styles.subtle}>
            {worker.nationality} · {worker.visa_type}
          </p>
        </div>
      </div>

      <section className={styles.split}>
        <div className={styles.stack}>
          <div className={cn(styles.card, styles.panel)} style={{ padding: 24 }}>
            <div className={styles.detailHeader}>
              <span className={styles.bigAvatar}>{initials}</span>
              <div>
                <h2>{worker.full_name ?? displayName}</h2>
                {tenure && <p className={styles.subtle}>근속 {tenure} · 외등록번호는 화면에 표시하지 않습니다.</p>}
              </div>
            </div>

            <div className={styles.infoGrid} style={{ marginTop: 20 }}>
              <InfoTile
                icon={<CalendarClock size={18} />}
                label="체류만료일"
                value={visaExpiry ? `${visaExpiry}${dday ? ` (${dday})` : ""}` : "정보 없음"}
              />
              <InfoTile
                icon={<CalendarClock size={18} />}
                label="계약종료일"
                value={contractEnd || "정보 없음"}
              />
              <InfoTile
                icon={<ShieldCheck size={18} />}
                label="비자 종류"
                value={worker.visa_type || "정보 없음"}
              />
            </div>
          </div>

          <div className={cn(styles.card, styles.panel)} style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>업무 메모</h2>
            <p className={styles.subtle} style={{ lineHeight: 1.7 }}>
              실제 상태 변경, 메시지 발송, 행정사 전달, 정부 제출은 에이전트 검토 후 담당자 승인이 필요합니다.
            </p>
          </div>
        </div>

        <aside className={styles.sideStack}>
          <div className={cn(styles.card, styles.panel)} style={{ padding: 20 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, marginBottom: 12 }}>추천 확인</h2>
            <div className={styles.stack}>
              <Button
                variant="secondary"
                disabled={agentLoading}
                onClick={() => void runAgent("서류 누락 현황과 요청 초안을 확인해줘", "서류 요청 초안 보기")}
              >
                {agentLoading && activeButton === "서류 요청 초안 보기" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : null}
                서류 요청 초안 보기
              </Button>
              <Button
                variant="secondary"
                disabled={agentLoading}
                onClick={() => void runAgent("행정사 검토 패키지 초안을 만들어줘", "행정사 검토 자료 보기")}
              >
                {agentLoading && activeButton === "행정사 검토 자료 보기" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : null}
                행정사 검토 자료 보기
              </Button>
              <Button
                variant="ghost"
                disabled={agentLoading}
                onClick={() => void runAgent("비자와 서류 현황을 요약해줘", "업무 기록 확인")}
              >
                {agentLoading && activeButton === "업무 기록 확인" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : null}
                업무 기록 확인
              </Button>
            </div>
            <p className={styles.safeNotice} style={{ marginTop: 14 }}>
              모든 액션은 승인 전 미리보기이며 외부 실행을 하지 않습니다.
            </p>
          </div>

          {agentResult && (
            <div className={cn(styles.card, styles.panel)} style={{ padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <h2 style={{ fontSize: 15, fontWeight: 800 }}>{activeButton}</h2>
                {agentResult.approvalRequired && (
                  <Badge tone="orange">담당자 승인 필요</Badge>
                )}
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.75, whiteSpace: "pre-wrap", color: "#1E293B" }}>
                {agentResult.text}
              </p>
            </div>
          )}

          <div className={cn(styles.card, styles.panel)} style={{ padding: 20 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, marginBottom: 12 }}>제출 서류</h2>
            <p className={styles.subtle} style={{ fontSize: 13 }}>
              서류 현황은 에이전트 검토 결과에서 확인하세요.
            </p>
          </div>
        </aside>
      </section>
    </div>
  );
}

function InfoTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className={styles.panel} style={{ display: "grid", gap: 8 }}>
      <span style={{ color: "#1d4ed8" }}>{icon}</span>
      <span className={styles.subtle}>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
