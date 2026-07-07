// D-day 계산·표기 — reference/specs/1단계_화면상태스펙_M1-M9_v1.md D-day 배지 규칙 (M0.3).
// dDay 부호 규칙: 양수=남은 일수(D-N), 0=만료 당일(D-day), 음수=경과(D+N).

export type DateInput = Date | string;

const MS_PER_DAY = 86_400_000;

// 'YYYY-MM-DD' / 'YYYY.MM.DD' / Date 를 UTC 자정 타임스탬프로 정규화한다.
// UTC 자정 기준이라 로컬 타임존·DST 영향 없이 일수 차이가 결정적이다.
function toUtcMidnight(value: DateInput): number {
  const date = typeof value === 'string' ? parseDate(value) : value;
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
}

function parseDate(value: string): Date {
  const match = value.match(/^(\d{4})[-.](\d{1,2})[-.](\d{1,2})/);
  if (match) {
    const [, y, m, d] = match;
    return new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`calcDday: 파싱할 수 없는 날짜 "${value}"`);
  }
  return parsed;
}

/** target 이 base 로부터 며칠 뒤인지. 미래=양수, 당일=0, 과거=음수. */
export function calcDday(target: DateInput, base: DateInput): number {
  return Math.round((toUtcMidnight(target) - toUtcMidnight(base)) / MS_PER_DAY);
}

/** 배지 라벨: D-N / D-day / D+N */
export function dDayLabel(dDay: number): string {
  if (dDay > 0) return `D-${dDay}`;
  if (dDay === 0) return 'D-day';
  return `D+${-dDay}`;
}

export type DDayTone = 'critical' | 'warning' | 'info' | 'neutral';

/**
 * 배지 색 규칙 (스펙 표):
 * 만료 경과(D+)·D-0 → critical(빨강) / D-1~30 → warning(주황)
 * / D-31~90 → info(파랑) / D-91+ → neutral(회색)
 */
export function dDayTone(dDay: number): DDayTone {
  if (dDay <= 0) return 'critical';
  if (dDay <= 30) return 'warning';
  if (dDay <= 90) return 'info';
  return 'neutral';
}
