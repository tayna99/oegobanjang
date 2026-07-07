import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { IconDoc, IconHome, IconList, IconMsg, IconSpark, IconWait } from './icons';

describe('탭 아이콘', () => {
  it.each([
    ['home', IconHome],
    ['list', IconList],
    ['msg', IconMsg],
    ['doc', IconDoc],
    ['spark', IconSpark],
    ['wait', IconWait],
  ] as const)('%s 아이콘이 svg를 렌더한다', (_name, Icon) => {
    const { container } = render(<Icon aria-hidden="true" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});
