# CLAUDE.md

이 파일은 Claude Code를 사용하는 팀원을 위한 루트 안내 문서입니다.

작업 규칙의 정본은 아래 파일입니다.

```txt
AGENTS.md
```

현행 운영 대상은 루트의 모바일 우선 Vite + React MVP이며, 작업은 주로 `src/`, `docs/`, `plans/`, `rules/`에서 이루어집니다. 이전 FastAPI 백엔드·데이터 파이프라인·Agent Runtime은 `legacy/`에 보관되어 있습니다.

작업 전 반드시 아래 문서를 확인합니다.

```txt
AGENTS.md
README.md
docs/ARCHITECTURE.md
docs/SPEC_INDEX.md
docs/GOTCHAS.md
plans/ROADMAP.md
plans/HANDOFF.md
rules/design.md
rules/frontend.md
rules/safety.md
```

Agent Runtime 관련 코드는 아래 경로에 보존되어 있으며, 복구/이관 mission이 명시된 경우에만 수정합니다.

```txt
legacy/backend/app/agent_runtime/
```

legacy 백엔드/Agent Runtime 작업 시에는 `legacy/docs/*`와 `legacy/missions/active/*.md`를 추가로 확인합니다.

현행 루트 MVP 검증은 아래 명령을 우선 사용합니다.

```bash
npm run verify
```

Claude는 구현 전에 짧은 계획을 먼저 작성하고, ROADMAP 태스크 또는 mission 범위 밖 파일은 수정하지 않습니다.
