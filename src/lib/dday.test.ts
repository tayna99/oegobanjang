import { describe, expect, it } from 'vitest';
import { calcDday, dDayLabel, dDayTone } from './dday';

const BASE = '2026-07-06'; // 기준일 주입 — new Date() 직접 호출 금지 규칙 준수

describe('calcDday — 경계값', () => {
  it('당일이면 0 (D-0)', () => {
    expect(calcDday('2026-07-06', BASE)).toBe(0);
  });

  it('30일 뒤면 30 (D-30)', () => {
    expect(calcDday('2026-08-05', BASE)).toBe(30);
  });

  it('90일 뒤면 90 (D-90)', () => {
    expect(calcDday('2026-10-04', BASE)).toBe(90);
  });

  it('경과하면 음수 (D+)', () => {
    expect(calcDday('2026-07-03', BASE)).toBe(-3);
  });

  it("'YYYY.MM.DD' 표기와 Date 입력도 동일하게 처리", () => {
    expect(calcDday('2026.08.05', BASE)).toBe(30);
    expect(calcDday(new Date(Date.UTC(2026, 7, 5)), new Date(Date.UTC(2026, 6, 6)))).toBe(30);
  });
});

describe('dDayLabel', () => {
  it.each([
    [30, 'D-30'],
    [90, 'D-90'],
    [0, 'D-day'],
    [-3, 'D+3'],
  ])('%i → %s', (dDay, label) => {
    expect(dDayLabel(dDay)).toBe(label);
  });
});

describe('dDayTone — 색 규칙 경계 (v2, 2026-07-11 새로 짬)', () => {
  it.each([
    [-3, 'critical'], // D+ 경과
    [0, 'critical'], // D-0
    [1, 'high'],
    [30, 'high'], // D-30 경계
    [31, 'medium'], // 진한 오렌지→흐린 오렌지 전환(v1은 파랑이었으나 v2는 블루=승인 필요 전용)
    [90, 'medium'], // D-90 경계
    [91, 'neutral'], // 오렌지→회색 플립
  ] as const)('dDay %i → %s', (dDay, tone) => {
    expect(dDayTone(dDay)).toBe(tone);
  });
});
