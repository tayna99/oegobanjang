import { z } from 'zod';
import { redirect } from 'react-router-dom';
import type { LoaderFunctionArgs } from 'react-router-dom';

// 딥링크 path param 검증 — rules/frontend.md "딥링크 파라미터는 zod로 파싱·검증".
// 영숫자·하이픈·언더스코어만 허용(형식 검증만). 케이스/스레드/런/패키지가
// 실제로 존재하는지는 스토어가 연결되는 태스크(1.4+)에서 검증한다.
const idParamSchema = z.string().min(1).regex(/^[a-zA-Z0-9_-]+$/);

export function validateIdParam(paramName: string) {
  return ({ params }: LoaderFunctionArgs): null => {
    const result = idParamSchema.safeParse(params[paramName]);
    if (!result.success) {
      throw redirect('/');
    }
    return null;
  };
}
