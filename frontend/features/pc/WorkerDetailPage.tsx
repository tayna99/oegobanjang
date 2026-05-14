"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, FileText, ShieldCheck } from "lucide-react";

import { workers } from "./data";
import { Badge, Button, cn } from "./ui";
import styles from "./PcShell.module.css";

type WorkerDetailPageProps = {
  workerId: string;
};

export function WorkerDetailPage({ workerId }: WorkerDetailPageProps) {
  const worker = workers.find((item) => item.id === workerId) ?? workers[0];
  const relatedWorkers = workers.filter((item) => item.line === worker.line && item.id !== worker.id).slice(0, 3);

  return (
    <div className={styles.stack}>
      <div className={styles.pageHead}>
        <div>
          <Link className={styles.pill} href="/workers">
            <ArrowLeft size={14} aria-hidden="true" />
            근로자 목록
          </Link>
          <h1 className={styles.headline} style={{ marginTop: 14 }}>{worker.name}</h1>
          <p className={styles.subtle}>
            {worker.nationalityCode} · {worker.nationality} · {worker.visaType} · {worker.line}
          </p>
        </div>
        <Badge tone={worker.statusTone}>{worker.status}</Badge>
      </div>

      <section className={styles.split}>
        <div className={styles.stack}>
          <div className={cn(styles.card, styles.panel)} style={{ padding: 24 }}>
            <div className={styles.detailHeader}>
              <span className={styles.bigAvatar}>{worker.initials}</span>
              <div>
                <h2>{worker.localName}</h2>
                <p className={styles.subtle}>근속 {worker.tenure} · 외등록번호는 화면에 표시하지 않습니다.</p>
              </div>
            </div>

            <div className={styles.infoGrid} style={{ marginTop: 20 }}>
              <InfoTile icon={<CalendarClock size={18} />} label="체류만료일" value={`${worker.visaExpiry} (${worker.dday})`} />
              <InfoTile icon={<CalendarClock size={18} />} label="계약종료일" value={worker.contractEnd} />
              <InfoTile icon={<ShieldCheck size={18} />} label="현재 상태" value={worker.status} />
            </div>
          </div>

          <div className={cn(styles.card, styles.panel)} style={{ padding: 24 }}>
            <div className={styles.sectionTitle}>
              <h2 style={{ fontSize: 16, fontWeight: 800 }}>제출 서류</h2>
              <Badge tone={worker.docExtra ? "orange" : "green"}>{worker.docExtra ? `보완 ${worker.docExtra}` : "확인됨"}</Badge>
            </div>
            <div className={styles.stack}>
              {worker.docs.map((doc, index) => (
                <div className={styles.docRow} key={`${doc}-${index}`}>
                  <FileText size={16} aria-hidden="true" />
                  <strong>{doc}</strong>
                  <Badge tone={worker.docExtra && index >= worker.docs.length - 1 ? "orange" : "green"}>
                    {worker.docExtra && index >= worker.docs.length - 1 ? "보완 필요" : "확보"}
                  </Badge>
                </div>
              ))}
            </div>
          </div>

          <div className={cn(styles.card, styles.panel)} style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12 }}>업무 메모</h2>
            <p className={styles.subtle} style={{ lineHeight: 1.7 }}>
              이 상세 화면은 현재 프론트 목데이터 기반의 운영 확인 화면입니다. 실제 상태 변경, 메시지 발송,
              행정사 전달, 정부 제출은 수행하지 않습니다.
            </p>
          </div>
        </div>

        <aside className={styles.sideStack}>
          <div className={cn(styles.card, styles.panel)} style={{ padding: 20 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, marginBottom: 12 }}>추천 확인</h2>
            <div className={styles.stack}>
              <Button variant="secondary">서류 요청 초안 보기</Button>
              <Button variant="secondary">행정사 검토 자료 보기</Button>
              <Button variant="ghost">업무 기록 확인</Button>
            </div>
            <p className={styles.safeNotice} style={{ marginTop: 14 }}>
              모든 액션은 승인 전 미리보기이며 외부 실행을 하지 않습니다.
            </p>
          </div>

          <div className={cn(styles.card, styles.panel)} style={{ padding: 20 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, marginBottom: 12 }}>같은 라인 근로자</h2>
            <div className={styles.stack}>
              {relatedWorkers.map((item) => (
                <Link className={styles.docRow} href={`/workers/${item.id}`} key={item.id}>
                  <span className={styles.workerAvatar}>{item.initials}</span>
                  <span>
                    <strong>{item.name}</strong>
                    <span className={styles.subtle} style={{ display: "block" }}>{item.status}</span>
                  </span>
                </Link>
              ))}
            </div>
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
