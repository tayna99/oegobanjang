@../AGENTS.md

# Claude Code Instructions

이 파일은 Claude Code를 사용하는 팀원을 위한 프로젝트 지침입니다.

---

## 1. 작업 전 반드시 읽기

Claude는 구현을 시작하기 전에 아래 파일을 먼저 읽습니다.

```txt
README.md
docs/PROJECT_BRIEF.md
docs/AI_OS_DESIGN.md
docs/RAG_STRATEGY.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
docs/EVAL_HARNESS.md
missions/active/*.md
```

---

## 2. 작업 기준

Agent 관련 코드는 아래 경로에서 관리합니다.

```txt
backend/app/agent_runtime/
```

---

## 3. 작업 원칙

1. 바로 구현하지 말고 먼저 짧은 계획을 작성한다.
2. mission 범위 밖 파일은 수정하지 않는다.
3. 승인 필요한 작업은 자동 실행하지 않는다.
4. 변경 후 테스트 또는 eval 실행 결과를 보고한다.
5. 민감정보 원문을 로그에 남기지 않는다.

---

## 4. 금지 작업

- AI 단독 비자 신청 제출
- AI 단독 법률·노무 자문
- 정부 포털 직접 자동 제출
- 근로자 SNS, 단톡방, 외부 커뮤니티 감시
- 이탈 예측
- 후보자 성실도 판단
- 국적별 선호 또는 차별적 추천
- 승인 없는 메시지 발송
- 승인 없는 행정사 패키지 전송

---

## 5. 완료 보고 형식

```md
## Plan

## Changed Files

## Implementation Summary

## Verification

## Risks

## Next Tasks
```