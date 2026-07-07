import { describe, expect, it } from 'vitest';
import { ROUTES } from './routes';

describe('ROUTES', () => {
  it('caseId를 포함한 경로를 만든다', () => {
    expect(ROUTES.case('nguyen')).toBe('/case/nguyen');
    expect(ROUTES.caseDraft('nguyen')).toBe('/case/nguyen/draft');
    expect(ROUTES.caseApprove('nguyen')).toBe('/case/nguyen/approve');
  });

  it('filter가 없으면 쿼리 없이 케이스 목록 경로를 만든다', () => {
    expect(ROUTES.cases()).toBe('/cases');
    expect(ROUTES.cases('crit')).toBe('/cases?filter=crit');
  });

  it('evidence는 ref 유무에 따라 쿼리를 붙인다', () => {
    expect(ROUTES.evidence()).toBe('/evidence');
    expect(ROUTES.evidence('4789')).toBe('/evidence?ref=4789');
  });

  it('파라미터 없는 경로는 상수 문자열이다', () => {
    expect(ROUTES.home).toBe('/');
    expect(ROUTES.messages).toBe('/messages');
    expect(ROUTES.done).toBe('/done');
    expect(ROUTES.onboardingWorkers).toBe('/onboarding/workers');
  });
});
