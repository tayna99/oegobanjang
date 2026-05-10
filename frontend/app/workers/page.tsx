import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function WorkersPage() {
  return (
    <RouteOverview
      title="근로자 현황"
      description="근로자별 체류, 서류, 연락 상태를 마스킹된 형태로 확인하는 화면입니다."
      items={[
        { label: "활성 근로자", value: "128명" },
        { label: "확인 필요", value: "7건", tone: "warning" },
        { label: "민감정보", value: "원문 비표시", tone: "info" },
      ]}
    />
  );
}
