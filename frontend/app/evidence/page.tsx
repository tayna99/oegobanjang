import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function EvidencePage() {
  return (
    <RouteOverview
      title="Evidence Log"
      description="검색 근거, 도구 실행, 승인 요청, 최종 응답 생성 이력을 민감정보 없이 추적합니다."
      items={[
        { label: "rag_retrieved", value: "공식 절차 근거" },
        { label: "approval_requested", value: "승인 요청 기록", tone: "warning" },
        { label: "PII 원문", value: "저장 금지", tone: "danger" },
      ]}
    />
  );
}
