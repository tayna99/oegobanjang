import Link from "next/link";
import {
  approvalItems,
  dashboardMetrics,
  dashboardTasks,
  documentGaps,
  evidenceEvents,
  hiringRequests,
  visaExpiries,
} from "@/features/dashboard/mockData";
import { DASHBOARD_REFRESH_LABEL } from "@/lib/constants";

function riskClass(risk: "low" | "medium" | "high") {
  if (risk === "high") {
    return "pill danger";
  }
  if (risk === "medium") {
    return "pill warning";
  }
  return "pill info";
}

export function DashboardShell() {
  return (
    <>
      <section className="hero">
        <span className="kicker">{DASHBOARD_REFRESH_LABEL}</span>
        <h2>이번 달 외국인 고용 운영 리스크를 먼저 봅니다.</h2>
        <p>
          비자 만료, 서류 누락, 신규 채용 요청, 승인 대기, Evidence Log를 한 화면에서 확인하는
          관리자용 MVP입니다. 실제 발송과 제출은 여기서 실행하지 않습니다.
        </p>
      </section>

      <section className="metric-grid" aria-label="핵심 지표">
        {dashboardMetrics.map((metric) => (
          <article className="card" key={metric.label}>
            <span className="kicker">{metric.label}</span>
            <strong className="big-number">{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="card">
          <div className="row">
            <h3>이번 달 처리 필요 업무</h3>
            <Link className="pill" href="/dashboard">
              전체 보기
            </Link>
          </div>
          <ul className="list">
            {dashboardTasks.map((task) => (
              <li className="list-item" key={task.id}>
                <div className="row">
                  <strong>{task.title}</strong>
                  <span className={riskClass(task.risk)}>{task.dueLabel}</span>
                </div>
                <span className="muted">{task.owner}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>비자 만료 임박 근로자</h3>
          <ul className="list">
            {visaExpiries.map((worker) => (
              <li className="list-item" key={worker.workerId}>
                <div className="row">
                  <strong>{worker.workerName}</strong>
                  <span className={worker.dDay <= 30 ? "pill danger" : "pill warning"}>
                    D-{worker.dDay}
                  </span>
                </div>
                <span className="muted">
                  {worker.workerId} · {worker.visaType}
                </span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>서류 누락 케이스</h3>
          <ul className="list">
            {documentGaps.map((gap) => (
              <li className="list-item" key={gap.caseId}>
                <strong>{gap.workerName}</strong>
                <span className="muted">{gap.missing.join(", ")}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>신규 채용 요청</h3>
          <ul className="list">
            {hiringRequests.map((request) => (
              <li className="list-item" key={request.requestId}>
                <div className="row">
                  <strong>{request.industry}</strong>
                  <span className="pill info">{request.headcount}명</span>
                </div>
                <span className="muted">{request.status}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>승인 대기 작업</h3>
          <ul className="list">
            {approvalItems.map((approval) => (
              <li className="list-item" key={approval.approvalId}>
                <strong>{approval.label}</strong>
                <span className="pill danger">approval_required</span>
                <span className="muted">차단 작업: {approval.blockedAction}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Evidence Log 최근 이력</h3>
          <ul className="list">
            {evidenceEvents.map((event) => (
              <li className="list-item" key={event.eventId}>
                <div className="row">
                  <strong>{event.eventType}</strong>
                  <span className="pill">{event.eventId}</span>
                </div>
                <span className="muted">{event.summary}</span>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </>
  );
}
