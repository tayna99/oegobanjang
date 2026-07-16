interface PlaceholderScreenProps {
  name: string;
}

// 화면 태스크가 아직 이 라우트를 구현하지 않았을 때의 자리표시자.
// 실제 화면(M1~M9)은 각 ROADMAP 태스크가 이 자리를 대체한다 — 케이스별로
// 복제하지 않고 이 컴포넌트 하나로 모든 미구현 라우트를 덮는다.
export function PlaceholderScreen({ name }: PlaceholderScreenProps) {
  return (
    <div className="p-5 text-muted">
      <p className="text-body2">{name} — 아직 구현되지 않았습니다.</p>
    </div>
  );
}
