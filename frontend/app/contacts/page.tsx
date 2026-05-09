import { RouteOverview } from "@/features/dashboard/RouteOverview";

export default function ContactsPage() {
  return (
    <RouteOverview
      title="다국어 연락"
      description="근로자와 외부 협력자에게 보낼 메시지 초안을 만들고 승인 상태를 확인합니다."
      items={[
        { label: "초안", value: "5건" },
        { label: "승인 필요", value: "2건", tone: "warning" },
        { label: "자동 발송", value: "비활성화", tone: "danger" },
      ]}
    />
  );
}
