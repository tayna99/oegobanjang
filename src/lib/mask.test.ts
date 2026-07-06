import { describe, expect, it } from 'vitest';
import { maskId } from './mask';

describe('maskId', () => {
  it('외국인등록번호: 구분자 유지, 숫자는 전부 마스킹', () => {
    expect(maskId('900101-1234567')).toBe('******-*******');
  });

  it('여권번호(영숫자)도 전부 마스킹', () => {
    expect(maskId('M12345678')).toBe('*********');
  });

  it('원문 숫자가 결과에 남지 않는다', () => {
    expect(maskId('900101-1234567')).not.toMatch(/[0-9]/);
  });

  it('빈 문자열은 그대로', () => {
    expect(maskId('')).toBe('');
  });
});
