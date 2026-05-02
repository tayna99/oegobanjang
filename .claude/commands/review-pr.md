# Review PR

## Purpose

PR이 외고반장 프로젝트 규칙, mission 범위, 안전 기준을 지키는지 검토한다.

## Required Reading

```txt
AGENTS.md
docs/AI_OS_DESIGN.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
docs/EVAL_HARNESS.md
관련 missions/active/*.md
```

## Review Checklist

- mission Scope를 지켰는가?
- 불필요한 파일 수정이 없는가?
- 테스트가 추가되었거나 통과했는가?
- eval case가 필요한 경우 추가되었는가?
- 승인 필요한 작업을 자동 실행하지 않는가?
- 금지 작업이 구현되지 않았는가?
- Evidence Log 후보 이벤트가 생성되는가?
- 민감정보 원문이 로그에 남지 않는가?
- API/DB/문서 변경이 서로 일치하는가?

## Output Format

```md
## Review Summary

## Blocking Issues

## Non-blocking Suggestions

## Safety Check

## Required Changes

## Approval Decision
```