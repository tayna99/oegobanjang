from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class PackageLinkStatus(BaseModel):
    """POST/GET .../link 공용 응답 — 문서 콘텐츠는 포함하지 않는다(R2.6 스코프 노트).

    프론트는 기존 mock 콘텐츠(mocks/packages.ts)를 그대로 렌더하고, 이 응답은 "링크가
    살아있는가"만 서버가 확정했다는 신호로만 쓴다.
    """

    case_id: str
    issued_at: dt.datetime
    expires_at: dt.datetime
