"""벡터 스토어 추상화 — 검색 로직(retriever)은 이 프로토콜만 알고, 구현은 교체 가능하다."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorHit:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float


class VectorIndex(Protocol):
    """컬렉션 1개에 대한 벡터 인덱스."""

    collection: str

    def upsert(self, records: list[VectorRecord]) -> int: ...

    def delete_source(self, source_id: str) -> int: ...

    def query(self, embedding: list[float], top_k: int) -> list[VectorHit]: ...

    def count(self) -> int: ...


def flatten_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """리스트 메타를 콤마 문자열로 평탄화 — legacy 인덱스·후필터 계약 유지."""
    output: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool | int | float | str):
            output[key] = value
        elif isinstance(value, list):
            output[key] = ",".join(str(item) for item in value)
        else:
            output[key] = json.dumps(value, ensure_ascii=False)
    return output


def matches_filters(metadata: dict[str, Any], filters: dict[str, str]) -> bool:
    """콤마 문자열 값·`ALL` 와일드카드를 지원하는 legacy 후필터 계약."""
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual == expected:
            continue
        if isinstance(actual, str):
            values = [item.strip() for item in actual.split(",") if item.strip()]
            if expected in values or "ALL" in values:
                continue
        return False
    return True
