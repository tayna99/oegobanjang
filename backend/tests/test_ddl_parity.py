"""DDL parity: SQLAlchemy 모델 ↔ 마이그레이션이 만든 실제 PG 스키마.

Alembic 0001이 `db/schema.sql`을 그대로 적용하므로 설계 킷과 백엔드 DDL은 **구조적으로 동일**하다
(드리프트 F5 원천 차단). 남는 드리프트 위험은 "모델이 실제 DB 컬럼과 어긋나는 것"뿐이므로,
이 테스트가 그것을 잡는다 — 31테이블 전부에 대해 모델 컬럼 집합·nullable·타입 카테고리가
information_schema와 일치하는지 대조한다.

이번 PR에서 실제로 났던 드리프트(예: 모델의 stale `drafts.sent_at`, 잘못된 case_citations PK)를
소급 재현하면 이 테스트가 잡아낸다.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Text,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB

import app.models as models

EXPECTED_TABLES = {
    "companies", "users", "memberships", "delegations", "workers", "citations",
    "document_requirements", "worker_documents", "worker_intake_files", "cases", "runs",
    "run_steps", "next_actions", "approvals", "case_citations", "evidence_events", "threads",
    "drafts", "draft_variants", "thread_messages", "interpretations", "status_update_proposals",
    "handoff_packages", "package_exports", "briefings", "briefing_items", "notifications",
    "csv_imports", "autonomy_grants", "agent_notes", "stat_snapshots",
}

MODEL_CLASSES = [getattr(models, name) for name in models.__all__]
MODELS_BY_TABLE = {cls.__tablename__: cls for cls in MODEL_CLASSES}


def _type_category(t) -> str:
    """SQLAlchemy 타입(모델 선언 또는 DB 반영)을 공통 카테고리로 매핑한다.

    JSONB→DateTime→Date 순서 주의: PG timestamptz는 DateTime 하위(TIMESTAMP)이고 Date가 아니다.
    Boolean은 Integer보다 먼저 검사(일부 방언에서 Boolean이 정수 계열일 수 있음).
    """
    if isinstance(t, JSONB):
        return "jsonb"
    if isinstance(t, Boolean):
        return "boolean"
    if isinstance(t, DateTime):
        return "timestamptz"
    if isinstance(t, Date):
        return "date"
    if isinstance(t, Integer):
        return "integer"
    if isinstance(t, Text):
        return "text"
    raise AssertionError(f"unmapped type {t!r}")


def test_model_table_set_matches_design():
    assert set(MODELS_BY_TABLE) == EXPECTED_TABLES


def test_migrated_db_has_exactly_the_expected_tables(session_engine):
    inspector = inspect(session_engine)
    actual = set(inspector.get_table_names(schema="public")) - {"alembic_version"}
    assert actual == EXPECTED_TABLES


@pytest.mark.parametrize("table", sorted(EXPECTED_TABLES))
def test_model_columns_match_db_columns(session_engine, table):
    inspector = inspect(session_engine)
    db_cols = {c["name"]: c for c in inspector.get_columns(table, schema="public")}
    model = MODELS_BY_TABLE[table]
    model_cols = {c.name: c for c in model.__table__.columns}

    assert set(model_cols) == set(db_cols), (
        f"[{table}] 모델↔DB 컬럼 집합 불일치: "
        f"모델에만={set(model_cols) - set(db_cols)}, DB에만={set(db_cols) - set(model_cols)}"
    )

    for name, mcol in model_cols.items():
        dbcol = db_cols[name]
        assert mcol.nullable == dbcol["nullable"], f"[{table}.{name}] nullable 불일치"
        mcat = _type_category(mcol.type)
        dcat = _type_category(dbcol["type"])
        assert mcat == dcat, f"[{table}.{name}] 타입 카테고리 불일치: 모델={mcat} DB={dcat}"
