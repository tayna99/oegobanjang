import { describe, expect, it } from 'vitest';
import { cn } from './cn';

describe('cn', () => {
  it('참인 클래스만 공백으로 결합한다', () => {
    expect(cn('a', false, undefined, 'b', null)).toBe('a b');
  });

  it('전부 falsy면 빈 문자열을 반환한다', () => {
    expect(cn(false, undefined, null)).toBe('');
  });
});
