import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlaceholderScreen } from './PlaceholderScreen';

describe('PlaceholderScreen', () => {
  it('전달된 화면 이름을 보여준다', () => {
    render(<PlaceholderScreen name="M2 케이스 시트" />);
    expect(screen.getByText(/M2 케이스 시트/)).toBeInTheDocument();
  });
});
