import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function HiringPage() {
  return (
    <RouteOverview
      title="인력확보"
      description="신규 채용 요청서, 후보 준비도, 송출회사 확인 질문을 초안 상태로 관리합니다."
      items={[
        { label: "신규 요청", value: "2건", tone: "info" },
        { label: "행정사 검토", value: "1건", tone: "warning" },
        { label: "후보 평가", value: "점수/추천 금지", tone: "danger" },
      ]}
    />
  );
}
