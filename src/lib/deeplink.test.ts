import { describe, expect, it } from 'vitest';
import type { LoaderFunctionArgs } from 'react-router-dom';
import { validateIdParam } from './deeplink';

function args(caseId: string): LoaderFunctionArgs {
  return {
    request: new Request(`http://localhost/case/${encodeURIComponent(caseId)}`),
    params: { caseId },
  } as unknown as LoaderFunctionArgs;
}

describe('validateIdParam', () => {
  it('영숫자·하이픈·언더스코어 id는 통과한다', () => {
    const loader = validateIdParam('caseId');
    expect(loader(args('nguyen'))).toBeNull();
  });

  it('빈 문자열이면 redirect(/)를 던진다', () => {
    const loader = validateIdParam('caseId');
    expect.assertions(2);
    try {
      loader(args(''));
    } catch (thrown) {
      const response = thrown as Response;
      expect(response.status).toBe(302);
      expect(response.headers.get('Location')).toBe('/');
    }
  });

  it('공백이 섞인 id는 redirect(/)를 던진다', () => {
    const loader = validateIdParam('caseId');
    expect.assertions(1);
    try {
      loader(args('a b'));
    } catch (thrown) {
      expect((thrown as Response).status).toBe(302);
    }
  });
});
