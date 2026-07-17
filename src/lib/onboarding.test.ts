import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useOnboardingActions } from './onboarding';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CompanyProfile } from '@/types';

const PROFILE: CompanyProfile = { name: '그린푸드 제조', region: '경기 화성', industry: '식품 제조업', workerCount: '6명' };

describe('useOnboardingActions.completeOnboarding', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useCompanyStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('로스터 전체를 caseStore에 반영하고(첫 근로자 등록 → 첫 카드 도달), 회사 프로필을 갱신하며(R1.1), evidence 1건을 남긴다', () => {
    const { result } = renderHook(() => useOnboardingActions());

    expect(useCaseStore.getState().cases.nguyen).toBeUndefined();

    act(() => result.current.completeOnboarding('manager', PROFILE));

    const cases = useCaseStore.getState().cases;
    expect(Object.keys(cases)).toHaveLength(CASE_CARDS.length);
    expect(cases.nguyen).toBeDefined();
    expect(cases.nguyen.title).toBe('체류기간 연장 서류 요청');

    expect(useCompanyStore.getState().profile).toEqual(PROFILE);

    const events = useEvidenceStore.getState().events;
    expect(events.some((e) => e.type === 'plan_created' && e.actor === '담당자 김담당')).toBe(true);
  });

  it('멱등 — 두 번 호출해도 케이스 수가 늘지 않는다', () => {
    const { result } = renderHook(() => useOnboardingActions());
    act(() => result.current.completeOnboarding('owner', PROFILE));
    act(() => result.current.completeOnboarding('owner', PROFILE));
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(CASE_CARDS.length);
  });
});
