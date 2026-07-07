// PII 마스킹 — reference/specs/3단계_온보딩플로우_v1.md §마스킹 저장 (M0.3).
// 외국인등록번호·여권번호 등 식별자는 화면·저장·로그에 원문을 남기지 않는다.
// 구분자(-, 공백 등)만 유지하고 모든 영숫자를 *로 치환한다. (예: 900101-1234567 → ******-*******)

export function maskId(raw: string): string {
  return raw.replace(/[A-Za-z0-9]/g, '*');
}
