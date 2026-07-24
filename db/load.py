"""db/ SQL 로더 — schema.sql · seed_reference.sql · seed_demo.sql을 순서대로 적용한다.

Windows 로컬에 psql 클라이언트가 없어도 되도록 uv 인라인 psycopg로 독립 실행한다
(db/validate.py와 동일 패턴 — SQL 파일이 정본이고, 이 러너는 로드만 한다. 생성 로직 없음).

로드 순서 계약: schema.sql → seed_reference.sql(모든 환경 필수) → seed_demo.sql(데모·로컬만).
seed_reference가 전역 A/B 근거·document_requirements를 먼저 넣어야 seed_demo의 case_citations
FK와 케이스 흐름이 풀린다.

Run:
  # 스키마 + 참조 시드만 (프로덕션 부트스트랩 근사)
  DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" \\
    uv run --no-project --with "psycopg[binary]" python db/load.py --reset --reference-only

  # 스키마 + 참조 + 데모 (로컬 개발·브라우저 검증)
  DATABASE_URL="..." uv run --no-project --with "psycopg[binary]" python db/load.py --reset --with-demo

플래그:
  --reset            대상 public 스키마를 drop/recreate 후 schema.sql 재적용 (파괴적).
  --reference-only   schema + seed_reference 까지만 (기본값).
  --with-demo        schema + seed_reference + seed_demo.

--reset 없이 실행하면(이미 스키마가 있는 DB에 시드만 재적용) schema.sql은 건너뛰고 시드만
적용을 시도한다 — 기존 시드가 있으면 PK 충돌로 실패하므로, 일반적으로 --reset과 함께 쓴다.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
).replace("postgresql+psycopg://", "postgresql://")

parser = argparse.ArgumentParser(description="Load db/ SQL files in dependency order")
parser.add_argument(
    "--reset",
    action="store_true",
    help="drop and recreate the target public schema, then re-apply schema.sql (destructive)",
)
mode = parser.add_mutually_exclusive_group()
mode.add_argument(
    "--reference-only",
    action="store_true",
    help="load schema + seed_reference only (production bootstrap; default)",
)
mode.add_argument(
    "--with-demo",
    action="store_true",
    help="load schema + seed_reference + seed_demo (local/demo)",
)
args = parser.parse_args()

conn = psycopg.connect(DATABASE_URL, autocommit=True)


def apply(name: str) -> None:
    conn.execute((DIR / name).read_text(encoding="utf-8"))
    print(f"applied  {name}")


if args.reset:
    conn.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
    apply("schema.sql")

# 참조 시드는 항상 로드한다(전 환경 필수).
apply("seed_reference.sql")

if args.with_demo:
    apply("seed_demo.sql")

conn.close()
mode_label = "schema + reference + demo" if args.with_demo else "schema + reference"
print(f"\nDone: {mode_label} loaded into {DATABASE_URL.rsplit('@', 1)[-1]}")
