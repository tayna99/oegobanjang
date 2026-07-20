import { describe, expect, it } from 'vitest';
import { resolveDeeplinkPath } from './deeplinkPath';

describe('resolveDeeplinkPath — R5.4', () => {
  it('case/{id}(/approve) 계열은 선행 슬래시만 붙인다', () => {
    expect(resolveDeeplinkPath('case/cs1')).toBe('/case/cs1');
    expect(resolveDeeplinkPath('case/cs1/approve')).toBe('/case/cs1/approve');
  });

  it('briefing은 홈으로', () => {
    expect(resolveDeeplinkPath('briefing')).toBe('/');
  });

  it('response/{threadId}는 스레드 경로로(§3 M6)', () => {
    expect(resolveDeeplinkPath('response/th_1')).toBe('/thread/th_1');
  });

  it('evidence/{eventId}는 evidence 쿼리 경로로(§3 M8)', () => {
    expect(resolveDeeplinkPath('evidence/4789')).toBe('/evidence?ref=4789');
  });

  it('onboarding/workers는 온보딩 경로로', () => {
    expect(resolveDeeplinkPath('onboarding/workers')).toBe('/onboarding');
  });

  it('run/{runId}은 선행 슬래시만 붙인다', () => {
    expect(resolveDeeplinkPath('run/run_1')).toBe('/run/run_1');
  });
});
