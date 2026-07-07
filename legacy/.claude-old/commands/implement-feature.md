# Implement Feature

## Purpose

Claude가 mission 범위 안에서 기능을 구현하게 만드는 명령 템플릿이다.

## Required Reading

```txt
AGENTS.md
docs/AI_OS_DESIGN.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
현재 작업에 해당하는 missions/active/*.md
```

## Instructions

1. mission의 Scope 안에서만 구현한다.
2. Target Files 외 파일은 가급적 수정하지 않는다.
3. 승인 필요한 작업은 실제 실행하지 않는다.
4. 금지 작업은 구현하지 않는다.
5. 필요한 테스트 또는 eval을 추가한다.
6. 변경 후 검증 명령을 실행하거나 실행 방법을 남긴다.

## Safety Rules

절대 구현하지 않는다.

```txt
AI 단독 비자 신청 제출
AI 단독 법률·노무 자문
정부 포털 직접 자동 제출
근로자 SNS/단톡방/외부 커뮤니티 감시
이탈 예측
후보자 성실도 판단
국적별 선호 또는 차별적 추천
```

## Output Format

```md
## Changed Files

## Implementation Summary

## Verification

## Risks

## Next Tasks
```