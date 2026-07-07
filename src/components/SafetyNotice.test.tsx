import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SafetyNotice } from './SafetyNotice';

describe('SafetyNotice', () => {
  it('고정 문구 "승인 전에는 외부 발송이 차단됩니다."를 그대로 렌더한다', () => {
    render(<SafetyNotice />);
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
  });

  it('shield 아이콘을 svg로 렌더한다', () => {
    const { container } = render(<SafetyNotice />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('props를 받지 않는 컴포넌트다 — 호출부가 문구를 바꿀 수 없다', () => {
    // SafetyNotice가 인자 없이 호출 가능해야 한다(파라미터 없는 컴포넌트).
    expect(SafetyNotice.length).toBe(0);
  });
});
