# CLAUDE.md

이 파일은 Claude Code를 사용하는 팀원을 위한 루트 안내 문서입니다.

상세 지침은 아래 파일을 따릅니다.

```txt
.claude/CLAUDE.md
```

작업 전 반드시 아래 문서를 확인합니다.

```txt
AGENTS.md
README.md
docs/PROJECT_BRIEF.md
docs/AI_OS_DESIGN.md
docs/RAG_STRATEGY.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
docs/EVAL_HARNESS.md
missions/active/*.md
```

Agent 관련 코드는 아래 경로에 둡니다.

```txt
backend/app/agent_runtime/
```

Claude는 구현 전에 짧은 계획을 먼저 작성하고, mission 범위 밖 파일은 수정하지 않습니다.