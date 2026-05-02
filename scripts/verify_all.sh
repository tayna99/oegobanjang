#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STRICT="${STRICT:-0}"

print_section() {
  echo ""
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

run_script_if_exists() {
  local script_path="$1"
  local label="$2"

  print_section "$label"

  if [ -s "$script_path" ]; then
    bash "$script_path"
  else
    echo "$script_path not found or empty."

    if [ "$STRICT" = "1" ]; then
      echo "STRICT=1, failing because required script is missing."
      exit 1
    fi

    echo "Skipping."
  fi
}

print_section "외고반장 전체 검증 시작"

echo "Project root: $ROOT_DIR"
echo "STRICT mode: $STRICT"

run_script_if_exists "scripts/run_backend_tests.sh" "1. Backend Tests"
run_script_if_exists "scripts/run_agent_tests.sh" "2. Agent Runtime Tests"
run_script_if_exists "scripts/run_frontend_tests.sh" "3. Frontend Tests"

print_section "4. Eval JSONL Syntax Check"

if [ -d "evals/datasets" ]; then
  python - <<'PY'
import json
from pathlib import Path

dataset_dir = Path("evals/datasets")
jsonl_files = sorted(dataset_dir.glob("*.jsonl"))

if not jsonl_files:
    print("No JSONL files found. Skipping JSONL syntax check.")
else:
    for path in jsonl_files:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    raise SystemExit(f"Invalid JSONL: {path}:{line_no} - {e}")

    print(f"Checked {len(jsonl_files)} JSONL files.")
PY
else
  echo "evals/datasets not found. Skipping JSONL syntax check."
fi

print_section "5. Eval Runner"

if [ -s "scripts/run_evals.py" ]; then
  if [ -f "evals/datasets/safety_guardrail_cases.jsonl" ]; then
    python scripts/run_evals.py --dataset safety_guardrail_cases
  else
    echo "evals/datasets/safety_guardrail_cases.jsonl not found. Skipping eval run."
  fi
else
  echo "scripts/run_evals.py not found or empty."

  if [ "$STRICT" = "1" ]; then
    echo "STRICT=1, failing because run_evals.py is missing."
    exit 1
  fi

  echo "Skipping eval runner."
fi

print_section "검증 완료"

echo "All available checks completed."