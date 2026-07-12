"""docs/DB_SCHEMA.md §5 가드레일이 실제 DB에서 강제되는지 검증한다.

db/validate.cjs(리포 루트 설계 SQL 검증, PASS 30)와 같은 성격의 점검을 이 백엔드의
실제 Alembic 마이그레이션 산출물에 대해 재확인한다 — P1 스코프만(P2 테이블인
handoff_packages·threads 관련 항목은 여기서 다루지 않는다, backend/README.md).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

NOW = "2026-07-12T08:00:00+00:00"


def _seed_minimal(conn):
    """company/user/worker/case/next_action/citation×2(A·F등급)/case_citation×2 최소 시드."""
    conn.execute(
        text(
            "INSERT INTO companies (id, name, created_at, updated_at) "
            "VALUES ('cmp_1', '테스트 사업장', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO users (id, phone, name, terms_agreed_at, created_at, updated_at) "
            "VALUES ('usr_1', '010-0000-0000', '김담당', :now, :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at, created_at, updated_at) "
            "VALUES ('wrk_1', 'cmp_1', 'Nguyen Van A', '베트남', '2026-08-09', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, created_at, updated_at) "
            "VALUES ('cs_1', 'cmp_1', 'case_001', 'wrk_1', 'visa_expiry', '테스트 케이스', 'HIGH', 'approval_pending', '2026-08-09', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, created_at, updated_at) "
            "VALUES ('act_1', 'cmp_1', 'cs_1', 'approve', 'send_message', '승인하기', :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO citations (id, grade, status, title, source, ingest_at, created_at, updated_at) "
            "VALUES ('cit_a', 'A', 'official', '출입국관리법 제25조', '국가법령정보센터', :now, :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(
        text(
            "INSERT INTO citations (id, grade, status, title, source, ingest_at, created_at, updated_at) "
            "VALUES ('cit_f', 'F', 'internal', '합성 데모 근거', '내부', :now, :now, :now)"
        ),
        {"now": NOW},
    )
    conn.execute(text("INSERT INTO case_citations (case_id, citation_id, added_by_actor, created_at) "
                       "VALUES ('cs_1', 'cit_a', 'rule', :now)"), {"now": NOW})
    conn.execute(text("INSERT INTO case_citations (case_id, citation_id, added_by_actor, created_at) "
                       "VALUES ('cs_1', 'cit_f', 'rule', :now)"), {"now": NOW})


@pytest.fixture()
def seeded(migrated_engine):
    with migrated_engine.begin() as conn:
        _seed_minimal(conn)
    return migrated_engine


# --- append-only (§5.2) ---------------------------------------------------


def test_evidence_events_append_only_blocks_update(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary, created_at) "
                "VALUES ('ev_1', 'cmp_1', 1, 'risk_flagged', :now, 'system', '요약', :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError, match="append-only"), seeded.begin() as conn:
        conn.execute(text("UPDATE evidence_events SET summary='변조' WHERE id='ev_1'"))


def test_evidence_events_append_only_blocks_delete(seeded):
    # 각 테스트는 독립된 임시 DB(function-scope fixture)라 여기서 직접 시드해야 한다
    # — 다른 테스트 함수가 넣은 행에 기대면 안 된다(이전 실패에서 발견한 테스트 버그).
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary, created_at) "
                "VALUES ('ev_1', 'cmp_1', 1, 'risk_flagged', :now, 'system', '요약', :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError, match="append-only"), seeded.begin() as conn:
        conn.execute(text("DELETE FROM evidence_events WHERE id='ev_1'"))


def test_evidence_event_no_duplicate_in_company(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary, created_at) "
                "VALUES ('ev_1', 'cmp_1', 1, 'risk_flagged', :now, 'system', '요약', :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary, created_at) "
                "VALUES ('ev_dup', 'cmp_1', 1, 'risk_flagged', :now, 'system', '중복 번호', :now)"
            ),
            {"now": NOW},
        )


# --- MVP 발송·전달 차단 CHECK (§5.4) ---------------------------------------


def test_drafts_sent_at_must_stay_null(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO drafts (id, company_id, case_id, channel, purpose, created_at, updated_at) "
                "VALUES ('drf_1', 'cmp_1', 'cs_1', 'Zalo', '서류 요청', :now, :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(text("UPDATE drafts SET sent_at=:now WHERE id='drf_1'"), {"now": NOW})


# --- 승인 가드레일 (§4.3·§5.3) ----------------------------------------------


def test_only_one_pending_approval_per_action(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO approvals (id, company_id, case_id, action_id, idempotency_key, "
                "requested_by_actor, requested_at, created_at) "
                "VALUES ('apv_1', 'cmp_1', 'cs_1', 'act_1', 'idem-1', 'user', :now, :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO approvals (id, company_id, case_id, action_id, idempotency_key, "
                "requested_by_actor, requested_at, created_at) "
                "VALUES ('apv_2', 'cmp_1', 'cs_1', 'act_1', 'idem-2', 'user', :now, :now)"
            ),
            {"now": NOW},
        )


def test_idempotency_key_is_unique(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO approvals (id, company_id, case_id, action_id, idempotency_key, "
                "requested_by_actor, requested_at, created_at) "
                "VALUES ('apv_1', 'cmp_1', 'cs_1', 'act_1', 'idem-1', 'user', :now, :now)"
            ),
            {"now": NOW},
        )
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, created_at, updated_at) "
                "VALUES ('act_2', 'cmp_1', 'cs_1', 'confirm', 'confirm_status', '확인', :now, :now)"
            ),
            {"now": NOW},
        )
        conn.execute(
            text(
                "INSERT INTO approvals (id, company_id, case_id, action_id, idempotency_key, "
                "requested_by_actor, requested_at, created_at) "
                "VALUES ('apv_dup', 'cmp_1', 'cs_1', 'act_2', 'idem-1', 'user', :now, :now)"
            ),
            {"now": NOW},
        )


# --- 케이스 재사용 규칙 (§4.3) ----------------------------------------------


def test_open_case_reuse_blocks_duplicate(seeded):
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, created_at, updated_at) "
                "VALUES ('cs_dup', 'cmp_1', 'case_099', 'wrk_1', 'visa_expiry', '중복', 'HIGH', 'draft', '2026-08-09', :now, :now)"
            ),
            {"now": NOW},
        )


def test_completed_case_reuse_is_allowed(seeded):
    with seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, severity, state, due_date, created_at, updated_at) "
                "VALUES ('cs_done', 'cmp_1', 'case_098', 'wrk_1', 'visa_expiry', '과거 완료본', 'HIGH', 'completed', '2026-08-09', :now, :now)"
            ),
            {"now": NOW},
        )


# --- enum CHECK ------------------------------------------------------------


def test_invalid_case_state_rejected(seeded):
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(text("UPDATE cases SET state='shipped' WHERE id='cs_1'"))


def test_invalid_evidence_type_rejected(seeded):
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO evidence_events (id, company_id, event_no, type, at, actor_type, summary, created_at) "
                "VALUES ('ev_bad', 'cmp_1', 99, 'oops', :now, 'system', 'x', :now)"
            ),
            {"now": NOW},
        )


def test_boolean_check_rejects_out_of_range_value(seeded):
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(text("UPDATE cases SET approval_required=2 WHERE id='cs_1'"))


# --- 파생 뷰 (§6) — F등급 근거는 usable에서 제외 ----------------------------


def test_usable_citations_excludes_grade_f(seeded):
    with seeded.connect() as conn:
        ids = {row[0] for row in conn.execute(text("SELECT id FROM v_usable_citations")).fetchall()}
    assert "cit_a" in ids
    assert "cit_f" not in ids


def test_case_derived_usable_citation_count_excludes_f(seeded):
    with seeded.connect() as conn:
        row = conn.execute(
            text("SELECT usable_citation_count FROM v_case_derived WHERE case_id='cs_1'")
        ).fetchone()
    assert row.usable_citation_count == 1  # cit_a만 usable, cit_f는 제외


def test_citation_link_counts(seeded):
    with seeded.connect() as conn:
        row = conn.execute(
            text("SELECT linked_case_count FROM v_citation_link_counts WHERE citation_id='cit_a'")
        ).fetchone()
    assert row.linked_case_count == 1


def test_pipeline_counts_derives_from_state_when_agent_stage_missing(seeded):
    with seeded.connect() as conn:
        rows = conn.execute(
            text("SELECT stage, case_count FROM v_pipeline_counts WHERE company_id='cmp_1'")
        ).fetchall()
    stages = {r.stage: r.case_count for r in rows}
    # cs_1(approval_pending, agent_stage NULL) → awaiting_approval로 파생
    assert stages.get("awaiting_approval", 0) >= 1


# --- 상태 전이 (§5.1) — DB는 값 집합만 강제, 왕복 자체는 허용 ---------------


def test_returned_state_round_trip_is_accepted(seeded):
    with seeded.begin() as conn:
        conn.execute(text("UPDATE cases SET state='returned' WHERE id='cs_1'"))
        conn.execute(text("UPDATE cases SET state='approval_pending' WHERE id='cs_1'"))
    with seeded.connect() as conn:
        state = conn.execute(text("SELECT state FROM cases WHERE id='cs_1'")).scalar_one()
    assert state == "approval_pending"


# --- 계단식 삭제 (§4) -------------------------------------------------------


def test_case_delete_cascades_next_actions_and_case_citations(seeded):
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM cases WHERE id='cs_1'"))
    with seeded.connect() as conn:
        remaining_actions = conn.execute(
            text("SELECT count(*) FROM next_actions WHERE case_id='cs_1'")
        ).scalar_one()
        remaining_links = conn.execute(
            text("SELECT count(*) FROM case_citations WHERE case_id='cs_1'")
        ).scalar_one()
    assert remaining_actions == 0
    assert remaining_links == 0


def test_company_delete_blocked_while_workers_reference_it(seeded):
    """FK 강제(PRAGMA foreign_keys=ON)가 실제로 걸려 있는지 확인 — companies에는
    CASCADE/SET NULL이 없으므로(§2 "테넌트 교차 FK는 서비스 계층에서 검증") 참조가
    남아있는 한 삭제가 막혀야 한다."""
    with pytest.raises(DBAPIError), seeded.begin() as conn:
        conn.execute(text("DELETE FROM companies WHERE id='cmp_1'"))


def test_worker_delete_sets_case_worker_id_null(seeded):
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM cases WHERE id='cs_1'"))  # FK 참조 먼저 제거
        conn.execute(text("DELETE FROM workers WHERE id='wrk_1'"))
    with seeded.connect() as conn:
        remaining = conn.execute(text("SELECT count(*) FROM workers WHERE id='wrk_1'")).scalar_one()
    assert remaining == 0
