import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StepTimeline } from './StepTimeline';
import type { RunStep } from '@/mocks/runs';

const STEPS: RunStep[] = [
  { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A · 베트남' },
  { kind: 'guardrail', label: '가드레일 정지', detail: '정부 포털 제출 불가' },
];

// 세로형 재설계(2.5.4b, Montage 공용 컴포넌트 §6) 계약:
// done=초록 체크 원 / streaming 시 마지막=파랑 펄스 링 / 가드레일=경고 톤 칩·라벨.
describe('StepTimeline', () => {
  it('각 스텝의 라벨과 상세를 렌더한다', () => {
    render(<StepTimeline steps={STEPS} />);
    expect(screen.getByText('근로자 프로필 확인 완료')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A · 베트남')).toBeInTheDocument();
    expect(screen.getByText('가드레일 정지')).toBeInTheDocument();
    expect(screen.getByText('정부 포털 제출 불가')).toBeInTheDocument();
  });

  it('guardrail 스텝은 경고 톤 칩·라벨로 다른 스텝과 구분된다 (GOTCHAS: 가드레일 노출)', () => {
    render(<StepTimeline steps={STEPS} />);
    // kind 칩: 가드레일 = high(경고) 톤, 일반 스텝 = neutral.
    expect(screen.getByText('가드레일')).toHaveClass('bg-warnbg');
    expect(screen.getByText('도구 실행')).toHaveClass('bg-neutbg');
    // 가드레일 라벨은 경고 색.
    expect(screen.getByText('가드레일 정지')).toHaveClass('text-warning');
    expect(screen.getByText('근로자 프로필 확인 완료')).toHaveClass('text-ink');
  });

  it('streaming이면 마지막 스텝 도트가 펄스 링(step-ring-pulse)으로 렌더된다', () => {
    const { container } = render(<StepTimeline steps={STEPS} streaming />);
    const dots = container.querySelectorAll('.step-ring-pulse');
    expect(dots).toHaveLength(1);
  });

  it('streaming이 아니면 펄스 링이 없다(전부 완료 표시)', () => {
    const { container } = render(<StepTimeline steps={STEPS} />);
    expect(container.querySelectorAll('.step-ring-pulse')).toHaveLength(0);
  });
});
