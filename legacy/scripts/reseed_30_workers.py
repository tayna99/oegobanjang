"""
30개 더미 근로자 데이터를 DB에 재시드합니다.

data-pipeline/seed/ CSV → daily_briefing_source_* 테이블 교체
"""

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_DIR = ROOT / "data-pipeline" / "seed"
DB_PATH = ROOT / "backend" / "data" / "oegobanjang.sqlite3"

NOW = datetime.now(timezone.utc).isoformat()


def load_csv(filename: str) -> list[dict]:
    with open(SEED_DIR / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mask_name(full_name: str) -> str:
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return full_name


def reseed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    workers = load_csv("workers.csv")
    docs = load_csv("worker_documents.csv")
    companies = load_csv("companies.csv")

    # 파생 테이블 초기화 (브리핑 캐시 무효화)
    derived = [
        "daily_briefing_results",
        "daily_briefing_cases",
        "daily_briefing_actions",
        "daily_briefing_approvals",
        "daily_briefing_evidence_events",
        "daily_briefing_handoff_previews",
        "daily_briefing_document_request_drafts",
        "daily_briefing_external_delivery_jobs",
        "daily_briefing_handoff_export_artifacts",
    ]
    for table in derived:
        cur.execute(f"DELETE FROM {table}")
        print(f"  cleared {table}")

    # source 테이블 초기화
    cur.execute("DELETE FROM daily_briefing_source_documents")
    cur.execute("DELETE FROM daily_briefing_source_workers")
    cur.execute("DELETE FROM daily_briefing_source_companies")
    print("  cleared source tables")

    # companies 시드 (5개)
    for c in companies[:5]:
        cur.execute(
            """
            INSERT INTO daily_briefing_source_companies
              (id, company_name, timezone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (c["id"], c["name"], "Asia/Seoul", NOW, NOW),
        )
    print(f"  inserted {min(len(companies), 5)} companies")

    # workers 시드 (30개)
    for w in workers:
        cur.execute(
            """
            INSERT INTO daily_briefing_source_workers
              (id, company_id, display_name_masked, raw_name,
               visa_expiry_date, contract_end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                w["id"],
                w["company_id"],
                mask_name(w["name"]),
                w["name"],
                w["visa_expires_at"],
                w["contract_ends_at"],
                NOW,
                NOW,
            ),
        )
    print(f"  inserted {len(workers)} workers")

    # documents 시드
    for d in docs:
        cur.execute(
            """
            INSERT INTO daily_briefing_source_documents
              (id, worker_id, document_type, status, required, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                d["id"],
                d["worker_id"],
                d["doc_type"],
                d["status"],
                1,
                NOW,
                NOW,
            ),
        )
    print(f"  inserted {len(docs)} documents")

    conn.commit()


def verify(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_briefing_source_companies")
    print(f"\n[검증] companies: {cur.fetchone()[0]}건")
    cur.execute("SELECT COUNT(*) FROM daily_briefing_source_workers")
    print(f"[검증] workers:   {cur.fetchone()[0]}건")
    cur.execute("SELECT COUNT(*) FROM daily_briefing_source_documents")
    print(f"[검증] documents: {cur.fetchone()[0]}건")
    cur.execute("SELECT DISTINCT company_id FROM daily_briefing_source_workers")
    companies = [r[0] for r in cur.fetchall()]
    print(f"[검증] company_id 종류: {len(companies)}개")
    cur.execute("SELECT display_name_masked, visa_expiry_date FROM daily_briefing_source_workers ORDER BY visa_expiry_date LIMIT 5")
    print("\n[검증] 체류만료 임박 TOP 5:")
    for row in cur.fetchall():
        print(f"  {row[0]:20s}  {row[1]}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"DB 파일 없음: {DB_PATH}")
        raise SystemExit(1)

    print(f"DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        print("\n[재시드 시작]")
        reseed(conn)
        verify(conn)
        print("\n완료.")
    finally:
        conn.close()
