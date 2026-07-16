import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BriefingHeader } from './BriefingHeader';

describe('BriefingHeader', () => {
  it('회사명과 날짜를 보여준다', () => {
    render(<BriefingHeader companyName="화성1공장" date="2026.07.06" unreadNotifications={0} />);
    expect(screen.getByText('화성1공장')).toBeInTheDocument();
    expect(screen.getByText('2026.07.06')).toBeInTheDocument();
  });
});
