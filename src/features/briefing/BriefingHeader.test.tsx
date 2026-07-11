import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BriefingHeader } from './BriefingHeader';

// M2.6.1(Mobile §2a): 큰 제목 "오늘 브리핑" + "날짜 · 사업장" 서브라인 + 알림 벨.
describe('BriefingHeader', () => {
  it('제목과 날짜·사업장 서브라인을 보여준다', () => {
    render(<BriefingHeader companyName="그린푸드 제조" date="7월 10일 (금)" unreadNotifications={0} />);
    expect(screen.getByRole('heading', { name: '오늘 브리핑' })).toBeInTheDocument();
    expect(screen.getByText('7월 10일 (금) · 그린푸드 제조')).toBeInTheDocument();
  });

  it('읽지 않은 알림이 있으면 벨에 도트를 표시한다', () => {
    const { container } = render(
      <BriefingHeader companyName="그린푸드 제조" date="7월 10일 (금)" unreadNotifications={2} />,
    );
    expect(container.querySelector('.bg-critical')).not.toBeNull();
  });
});
