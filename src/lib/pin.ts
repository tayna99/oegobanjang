// 승인 PIN 목업(4.3) — 실제 인증 백엔드 없음. 형식만 검사하면 "본인확인 게이트"가
// 체감되지 않아 고정 데모값 일치를 검사한다(발표자 실패 방지로 시트에 값을 노출).
export const DEMO_PIN = '1234';

export function isValidPinFormat(input: string): boolean {
  return /^\d{4}$/.test(input);
}
