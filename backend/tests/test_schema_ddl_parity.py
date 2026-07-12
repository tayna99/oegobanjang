"""마이그레이션이 실제로 만든 DDL이 docs/DB_SCHEMA.md §10(P1 18테이블)·§6(파생 뷰 4종)·
§5.2(append-only 트리거 2종)와 일치하는지 구조 단위로 검증한다.

컬럼 단위 세부 검증은 db/validate.cjs(리포 루트 SQL 설계)의 몫 — 여기는 "SQLAlchemy
모델이 스키마 설계와 같은 표면적을 갖는가"만 본다(테이블/뷰/트리거 이름 집합).
"""

from sqlalchemy import inspect, text

# docs/DB_SCHEMA.md §10 P1 코어 18테이블
EXPECTED_P1_TABLES = {
    "companies",
    "users",
    "memberships",
    "workers",
    "citations",
    "case_citations",
    "document_requirements",
    "worker_documents",
    "cases",
    "next_actions",
    "approvals",
    "evidence_events",
    "runs",
    "run_steps",
    "drafts",
    "draft_variants",
    "briefings",
    "briefing_items",
}

EXPECTED_VIEWS = {
    "v_usable_citations",
    "v_citation_link_counts",
    "v_case_derived",
    "v_pipeline_counts",
}

EXPECTED_TRIGGERS = {
    "evidence_events_no_update",
    "evidence_events_no_delete",
}


def test_p1_table_set_matches_design(migrated_engine):
    inspector = inspect(migrated_engine)
    actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert actual_tables == EXPECTED_P1_TABLES


def test_view_set_matches_design(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='view'")).fetchall()
    assert {r[0] for r in rows} == EXPECTED_VIEWS


def test_trigger_set_matches_design(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).fetchall()
    assert {r[0] for r in rows} == EXPECTED_TRIGGERS


def test_no_fk_violations_on_fresh_schema(migrated_engine):
    with migrated_engine.connect() as conn:
        violations = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
    assert violations == []


def test_integrity_check_ok(migrated_engine):
    with migrated_engine.connect() as conn:
        result = conn.execute(text("PRAGMA integrity_check")).fetchone()
    assert result[0] == "ok"


def test_p1_scope_boundary_drafts_thread_id_has_no_fk(migrated_engine):
    """drafts.thread_id는 P2(threads) 도입 전까지 FK가 없어야 한다(backend/README.md 스코프 경계)."""
    inspector = inspect(migrated_engine)
    fks = inspector.get_foreign_keys("drafts")
    referred_tables = {fk["referred_table"] for fk in fks}
    assert "threads" not in referred_tables
    columns = {c["name"] for c in inspector.get_columns("drafts")}
    assert "thread_id" in columns  # 컬럼 자체는 존재(값만 있고 FK 제약 없음)
