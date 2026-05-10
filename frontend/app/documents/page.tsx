import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function DocumentsPage() {
  return (
    <RouteOverview
      title="서류"
      description="누락 서류와 제출 준비 상태를 확인하고 Evidence Log와 연결합니다."
      items={[
        { label: "누락 케이스", value: "2건", tone: "warning" },
        { label: "템플릿 초안", value: "3개" },
        { label: "자동 제출", value: "차단", tone: "danger" },
      ]}
    />
  );
}
