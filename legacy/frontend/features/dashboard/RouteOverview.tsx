type RouteOverviewProps = {
  title: string;
  description: string;
  items: Array<{
    label: string;
    value: string;
    tone?: "info" | "warning" | "danger";
  }>;
};

function toneClass(tone: RouteOverviewProps["items"][number]["tone"]) {
  if (tone === "danger") {
    return "pill danger";
  }
  if (tone === "warning") {
    return "pill warning";
  }
  return "pill info";
}

export function RouteOverview({ title, description, items }: RouteOverviewProps) {
  return (
    <>
      <section className="route-header">
        <span className="kicker">MVP skeleton</span>
        <h2>{title}</h2>
        <p className="muted">{description}</p>
      </section>
      <section className="route-grid">
        {items.map((item) => (
          <article className="card" key={item.label}>
            <span className="kicker">{item.label}</span>
            <p className={toneClass(item.tone)}>{item.value}</p>
          </article>
        ))}
        <article className="empty-action">
          실제 발송, 행정사 전달, 정부 제출은 이 화면에서 직접 실행하지 않습니다.
          담당자 승인 이후에도 내부 준비 상태만 전환합니다.
        </article>
      </section>
    </>
  );
}
