// 가드레일 위반 시 던지는 에러. GOTCHAS의 금지가 코드로 가능해지면 이 에러로 표면화한다.
export class GuardrailError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GuardrailError';
  }
}
