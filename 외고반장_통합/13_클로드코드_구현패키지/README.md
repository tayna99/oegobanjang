# 외고반장 — Claude Code 구현 하네스 패키지

> 작성일: 2026-07-04
> 목적: 이 폴더를 새 저장소 루트에 복사하면, Claude Code가 길을 잃지 않고 외고반장 모바일 퍼스트 MVP를 구현할 수 있는 **작업 환경(하네스)**이 된다.
> 설계 근거: 업로드된 4개 강의 리포트(하네스 엔지니어링 4기둥·6축, 에이전틱 엔지니어링 5개념, AI-Ready 코드베이스, 토큰 최적화) × 기존 `12_모바일퍼스트_재설계` 설계 문서 9종 × 프로토타입 v3

---

## 1. 하네스 4기둥 → 이 패키지의 매핑

| 기둥 | 이 패키지에서 | 파일 |
|---|---|---|
| 맥락 (Context) | 프로젝트 규칙은 가볍게, 상세는 필요할 때 로드 (Progressive Disclosure) | `CLAUDE.md`(≤150줄) + `rules/` + `docs/` |
| 제한 (Constraints) | 도메인 가드레일 + 코드 금지 패턴 | `docs/GOTCHAS.md`, `rules/safety.md` |
| 작업 흐름 (Orchestration) | 마일스톤·태스크 스펙·위임 레벨 | `plans/ROADMAP.md`, `.claude/agents/` |
| 검증 (Verification) | 태스크별 완료 기준 + 자동 훅 + 검증 서브에이전트 | `plans/ROADMAP.md`의 DoD, `.claude/settings.example.json`, `.claude/agents/verifier.md` |

## 2. 사용법 (새 저장소 세팅 순서)

```
1. 새 repo 생성 → 이 폴더 내용물을 루트에 복사
   (CLAUDE.md, docs/, rules/, plans/, claude-config/)
2. claude-config/ 폴더 이름을 .claude/ 로 변경
   → .claude/settings.example.json 을 .claude/settings.json 으로 복사 (훅 활성화)
   → .claude/agents/ 의 verifier·ui-matcher 서브에이전트 자동 인식
3. 참조 자산 복사:
   - reference/prototype_v3.html   ← 12_…/2026-07-04_5단계_프로토타입_v3.html
   - reference/specs/              ← 12_ 폴더의 1~9단계 + 탭별기획 md (읽기 전용 스펙 원본)
4. Claude Code 실행 → 첫 프롬프트:
   "plans/ROADMAP.md의 M0부터 시작해줘. 각 태스크는 명시된 스펙 파일을 먼저 읽고,
    완료 선언 전에 verifier 서브에이전트를 호출해. UI 태스크는 ui-matcher도."
```

## 3. 세션 운영 규칙 (강의 리포트 준용 — 사람이 지킬 것)

- **컨텍스트 20~40% 규칙**: 상태줄로 포화도 상시 확인. 40% 넘으면 미련 없이 새 세션 — 진행 상황은 `plans/HANDOFF.md`에 기록시키고 이어받기. 50% 이후 산출물은 버린다는 각오로.
- **태스크 1개 = 세션 1개**가 기본. ROADMAP의 태스크는 그 크기로 잘라뒀다.
- **위임 스펙트럼** (ROADMAP의 각 태스크에 표기):
  - L1 완전 자율: 보일러플레이트, 토큰 치환, 컴포넌트 이식 → 결과만 확인
  - L2 계획 승인 후 위임: 신규 화면, 라우팅, 상태 스토어 → plan 모드로 계획 받고 승인
  - L3 협업: 에이전트 런타임(툴콜링 루프), 승인 게이트 → 단계마다 개입
  - 판단 기준: "내가 결과를 빠르게 검증할 수 있는가?"
- **검증 없는 완료 선언 금지**: 모든 태스크는 DoD의 명령(test/lint/build)이 기준. 프로토타입과의 눈 비교는 스크린샷으로.
- **개선 축(6축의 마지막)**: 에이전트가 같은 실수를 2번 하면 그 자리에서 `rules/`에 규칙으로 박제하고 커밋한다. 하네스는 쓸수록 단단해져야 한다.

## 4. AI-Ready 코드베이스 원칙 (Sanity + Cartography)

- **Sanity 먼저**: M0에서 테스트 러너·lint·typecheck·CI를 코드보다 먼저 세팅한다. 테스트는 에이전트의 셀프 검증 신호다.
- **Cartography**: `docs/ARCHITECTURE.md`(진입점·의존 방향·흐름도), `docs/GLOSSARY.md`(도메인 용어), `docs/GOTCHAS.md`(함정)가 에이전트용 지도다. **코드 변경으로 지도가 낡으면 같은 PR에서 갱신** — 지도가 거짓말하면 없느니만 못하다.
- **컨벤션은 하나만**: 같은 일을 하는 두 패턴을 남기지 않는다(에이전트가 잘못된 패턴을 일반화함). 데드 코드는 즉시 삭제.
- **모듈 CLAUDE.md**: `src/features/*` 가 커지면 폴더 레벨 CLAUDE.md를 추가한다(가까운 규칙이 이긴다).

## 5. 토큰 최적화 규칙

- CLAUDE.md는 150줄 이하 유지 — 여기 넣고 싶은 게 생기면 `rules/`로 보내고 포인터만 남긴다
- 바뀌지 않는 규칙(문서 앞부분)과 바뀌는 정보(작업 지시)를 분리해 캐시 적중률 확보
- 스펙 원본(reference/specs)은 **필요한 파일만** 읽게 한다 — "12_ 폴더 전부 읽어줘" 금지
- 안 쓰는 MCP·스킬은 세션에서 제거

## 6. 이 패키지의 파일 지도

```
CLAUDE.md                     프로젝트 헌법 (가볍게)
docs/ARCHITECTURE.md          에이전트용 지도: 구조·진입점·데이터 흐름
docs/GLOSSARY.md              도메인 용어집 (한/영 코드 네이밍 포함)
docs/GOTCHAS.md               도메인 가드레일 + 코드 함정 (절대 규칙)
docs/SPEC_INDEX.md            기존 설계 문서 ↔ 구현 매핑 지도
rules/frontend.md             프론트 컨벤션 (필요 시 로드)
rules/design.md               디자인 토큰·UI 규칙 (필요 시 로드)
rules/safety.md               도메인 안전 체크리스트 (발송·PII·표현)
plans/ROADMAP.md              마일스톤 M0~M4 · 태스크 스펙 · DoD · 위임 레벨
plans/HANDOFF.md              세션 인수인계 기록 (에이전트가 갱신)
claude-config/                → repo에서 .claude/ 로 이름 변경
  settings.example.json       훅: 편집 후 lint·PII 스캔, Stop 시 verify
  agents/verifier.md          검증 서브에이전트 (가드레일·DoD 판정 전담)
  agents/ui-matcher.md        UI 대조 서브에이전트 (프로토타입 v3 대비)
plans/HANDOFF.md              세션 인수인계 기록 (에이전트가 갱신)
```
