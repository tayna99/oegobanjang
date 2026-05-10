import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function ApprovalsPage() {
  return (
    <RouteOverview
      title="승인 대기"
      description="외부 전달, 발송, 상태 완료 처리 전에 담당자 승인이 필요한 작업을 모읍니다."
      items={[
        { label: "PENDING", value: "2건", tone: "warning" },
        { label: "내부 완료 가능", value: "초안 확정/패키지 준비" },
        { label: "외부 실행", value: "후속 mission", tone: "danger" },
      ]}
    />
  );
}
