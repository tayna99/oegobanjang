import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function VisaPage() {
  return (
    <RouteOverview
      title="비자·체류"
      description="체류기간과 갱신 준비 상태를 보여주되, 비자 가능 여부를 AI가 확정하지 않습니다."
      items={[
        { label: "D-30 이내", value: "1명", tone: "danger" },
        { label: "검토 필요", value: "4건", tone: "warning" },
        { label: "최종 판단", value: "행정사 검토 필요", tone: "info" },
      ]}
    />
  );
}
