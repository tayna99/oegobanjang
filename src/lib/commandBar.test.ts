import { describe, expect, it } from 'vitest';
import { DEFAULT_COMMAND_RUN_KEY, resolveCommandRunKey } from './commandBar';

// R1.6 DoD — "추천 칩 즉시 제출 + 입력→런 매핑 테이블".
describe('resolveCommandRunKey', () => {
  it('빈 입력은 기본 command 런(#4797)으로 폴백한다', () => {
    expect(resolveCommandRunKey('')).toBe(DEFAULT_COMMAND_RUN_KEY);
    expect(resolveCommandRunKey('   ')).toBe(DEFAULT_COMMAND_RUN_KEY);
  });

  it('매칭되는 워커명이 없으면 기본 command 런으로 폴백한다', () => {
    expect(resolveCommandRunKey('이번 달 급한 직원만 정리해줘')).toBe(DEFAULT_COMMAND_RUN_KEY);
    expect(resolveCommandRunKey('오늘 승인 대기 요약해줘')).toBe(DEFAULT_COMMAND_RUN_KEY);
  });

  it('워커명이 포함되면(대소문자 무관) 그 워커의 승인 런으로 연결한다', () => {
    expect(resolveCommandRunKey('Nguyen 씨한테 서류 요청해줘')).toBe('nguyen');
    expect(resolveCommandRunKey('nguyen 승인 부탁')).toBe('nguyen');
    expect(resolveCommandRunKey('Siti 신고서 확인해줘')).toBe('siti');
    expect(resolveCommandRunKey('Batbayar 패키지 전달 준비해줘')).toBe('batbayarPkg');
  });
});
