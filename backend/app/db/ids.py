"""애플리케이션 PK 발급 단일 지점 — UUIDv7(시간순 정렬 가능, docs/DB_SCHEMA.md §2).

Python 3.14+ 표준 라이브러리 `uuid.uuid7()`를 사용한다(외부 라이브러리 불채택).
"""

import uuid


def new_id() -> str:
    return str(uuid.uuid7())
