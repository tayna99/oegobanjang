from __future__ import annotations

import pytest

_pg_available: bool | None = None


def _check_pg() -> bool:
    global _pg_available
    if _pg_available is None:
        try:
            import sqlalchemy

            from oe_rag.config import pg_url

            engine = sqlalchemy.create_engine(pg_url())
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            engine.dispose()
            _pg_available = True
        except Exception:
            _pg_available = False
    return _pg_available


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "pgvector" in item.keywords and not _check_pg():
            item.add_marker(
                pytest.mark.skip(reason="pgvector PostgreSQL unreachable (set RAG_PG_URL)")
            )
