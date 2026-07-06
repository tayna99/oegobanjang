// 조건부 클래스 결합 유틸 — legacy/frontend/features/pc/ui.tsx의 cn() 그대로 승계
// (6단계_기존코드_갭분석_v1.md §3.1 "그대로 재사용").
export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(' ');
}
