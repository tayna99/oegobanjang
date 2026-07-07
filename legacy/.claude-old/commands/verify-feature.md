# Verify Feature

## Purpose

구현된 기능이 mission의 Acceptance Criteria와 안전 기준을 만족하는지 검증한다.

## Required Reading

```txt
docs/EVAL_HARNESS.md
docs/SECURITY_GUARDRAILS.md
docs/EVIDENCE_LOG_SCHEMA.md
현재 작업에 해당하는 missions/active/*.md
```

## Checklist

- 테스트가 통과하는가?
- eval이 통과하는가?
- 승인 필요한 작업이 자동 실행되지 않는가?
- 금지 작업이 구현되지 않았는가?
- Evidence Log 후보 이벤트가 생성되는가?
- 민감정보 원문이 로그에 남지 않는가?
- mission Scope 밖 수정이 없는가?

## Recommended Commands

```bash
bash scripts/run_backend_tests.sh
bash scripts/run_agent_tests.sh
bash scripts/run_frontend_tests.sh
python scripts/run_evals.py --dataset safety_guardrail_cases
```

## Output Format

```md
## Verification Summary

## Tests Run

## Eval Results

## Safety Check

## Evidence Log Check

## Remaining Risks
```