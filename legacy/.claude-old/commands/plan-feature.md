# Plan Feature

## Purpose

Claude가 구현을 시작하기 전에 작업 범위, 수정 파일, 위험 요소, 검증 방법을 먼저 정리하게 만드는 명령 템플릿이다.

## Required Reading

작업 전 아래 문서를 확인한다.

```txt
AGENTS.md
README.md
docs/PROJECT_BRIEF.md
docs/ARCHITECTURE.md
docs/AI_OS_DESIGN.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
missions/active/*.md
```

## Instructions

1. 바로 코드를 수정하지 않는다.
2. 관련 mission을 먼저 확인한다.
3. Scope와 Out of Scope를 구분한다.
4. 수정할 파일 목록을 작성한다.
5. 테스트/eval 방법을 작성한다.
6. 승인 필요 작업 또는 금지 작업이 포함되는지 확인한다.

## Output Format

```md
## Goal

## Related Mission

## Target Files

## Plan

## Out of Scope

## Verification

## Risks
```