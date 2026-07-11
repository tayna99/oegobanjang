# ROADMAP — 마일스톤 · 태스크 스펙 · DoD

> 태스크 1개 = Claude Code 세션 1개 크기. 순서대로. 각 태스크: 위임 레벨(L1 자율 / L2 계획 승인 / L3 협업) + 읽을 스펙 + DoD(검증 명령).
> 진행 기록은 `plans/HANDOFF.md`에 남긴다 (에이전트가 태스크 종료 시 갱신).

## M0 — Sanity 기반 (코드보다 검증 먼저)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 0.1 | Vite+React+TS+Tailwind+router+zustand 스캐폴드, `npm run verify` 스크립트 구성 | L1 | — | `verify` 통과, 빈 앱 렌더 |
| 0.2 | `styles/tokens.css` + tailwind theme 연동 (v3 `:root` 이식) | L1 | prototype_v3, rules/design.md | 토큰 스냅샷 테스트 1개 |
| 0.3 | `src/types.ts` 데이터 타입 + `calcDday`·`maskId` 유틸 + 단위 테스트 | L1 | 1단계 §0.4 | dDay 경계값(D+, D-0, D-30, D-90) 테스트 통과 |
| 0.4 | 스토어 3종(case/approval/evidence) + **가드레일 테스트** | L2 | GOTCHAS §1·2 | "승인 없이 dispatch 불가"·"evidence append-only"·"중복 승인 차단" 테스트 통과 |
| 0.5 | mocks 이식 (v3의 CASE/DRAFT/APPROVE/EV → fixtures) | L1 | SPEC_INDEX 이식표 | typecheck 통과, PII 원문 없음 검사 |

## M1 — 셸과 승인 해피패스 (데모 3막의 뼈대)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 1.1 | 라우터+딥링크 맵, Shell(모바일 탭바/PC 헤더 분기) | L2 | 2단계 §3, 탭별기획 §0 | 라우트 스냅샷 테스트, 딥링크 백스택 = M1→목적지 |
| 1.2 | 공용 컴포넌트: Button/Badge/Card/SafetyNotice/OfflineBanner/Skeleton | L1 | 1단계 §0.2·0.3, rules/design.md | 스토리 렌더 테스트, 배지 색 규칙 테이블 테스트 |
| 1.3 | M1 브리핑 홈 (5상태 전부: default/empty/loading/error/offline) | L2 | 1단계 M1, 탭별기획 §1 | 상태별 렌더 테스트 5개, empty에 온보딩 유도 |
| 1.4 | BottomSheet + M2 케이스 시트 (데이터 구동, 케이스별 복제 금지) | L2 | 1단계 M2, GOTCHAS §4 | citation 0건 → 승인 locked 테스트 |
| 1.5 | 런 엔진 + StepTimeline (mode: approval/command/replay, 스텝 스트리밍) | **L3** | 1단계 M9 v1.2, ARCHITECTURE §5 | 스트리밍 완료 전 승인 disabled 테스트, guardrail 스텝 렌더 |
| 1.6 | M3 초안(언어 토글·수정 요청 시트) + M4 승인 + M5 완료 + 상태 전파 | L2 | 1단계 M3~M5 | **E2E: 알림딥링크→M1→M2→M3→M4→M5→M1 상태 반영** (playwright) |

## M2 — 나머지 탭 (확인 면)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.1 | M7 케이스 목록 (필터 칩·그룹·딥링크 프리셋) | L1 | 1단계 M7, 탭별기획 §2 | 필터·정렬 deterministic 테스트 |
| 2.2 | 메시지 탭 + 스레드 대화 뷰 + M6 응답 해석(isFinal:false→확인) — **완료** (`plans/HANDOFF.md` 2026-07-11 항목 참고) | L2 | 1단계 M6, 탭별기획 §3 | 해석 확인 시 상태 갱신+evidence 테스트 |
| 2.3 | M8 판단 기록 (타임라인·필터·이벤트 상세 시트·딥링크 하이라이트) | L1 | 1단계 M8, 탭별기획 §4 | 해시만 표시(원문 없음) 테스트 |
| 2.4 | 행정사 패키지 화면 (candidate/hiring 데이터 구동) | L1 | prototype_v3 pkg | 승인 흐름 단계 렌더 테스트 |

## M3 — 에이전틱 차별화 (9단계 P0)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 3.1 | 프로액티브 런: 이벤트→자동 런→카드 `preparedBy:'agent'`+재생 뷰 | **L3** | 9단계 P0-1, 1단계 v1.2 | 재생 뷰 읽기 전용, 가드레일 정지 스텝 존재 테스트 |
| 3.2 | 커맨드 바 → M9 사용자 런 → 결과 카드 → 케이스 연결 | L2 | 1단계 M9 | 런 1건=evidence 1건 테스트 |
| 3.3 | 케이스 에이전트 활동 타임라인(런 체이닝)+nextWake | L2 | 9단계 P0-2 | 체인 렌더 테스트 |
| 3.4 | 데모 폴리시: 8단계 4막 대본 그대로 시연 가능 상태 점검 | L1 | 8단계 | 데모 체크리스트 전 항목 수동 확인 + E2E 스모크 |

## M4 — 온보딩·권한 (파일럿 준비)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 4.1 | 온보딩 O1~O5 (수기 4필드 → 첫 브리핑 동기 생성 연출) | L2 | 3단계 | E2E: 근로자 1명 등록→첫 카드 도달 |
| 4.2 | 역할 분기(owner/manager 홈·권한 가드) | L2 | 7단계 §2·6 | 라우트 가드 테스트 (owner의 M9 쓰기 도구 차단) |
| 4.3 | 승인 본인확인 목업(PIN) + 대리 승인 배지 | L2 | 7단계 §3·4 | 승인 이벤트에 결정자·본인/대리 기록 |

## 백엔드 접속점 (이후 — 별도 계획)

- mockApi → FastAPI(기존 Daily Briefing PRD 백엔드)로 교체. 계약: `src/types.ts` = PRD §11 Data Contracts
- runEngine 각본 → LangGraph createAgent 스트리밍으로 교체 (RunConfig 인터페이스 유지)
- 발송 어댑터·알림톡은 계속 범위 밖 (승인 기반 어댑터, PRD Sprint 6)¹

¹ outbox(발송 대기열)+`SmsAdapter`+응답 링크 인바운드까지의 로드맵은 `docs/MESSAGING_CHANNELS.md` §5(단계 로드맵)에 정리돼 있다 — 이 저장소는 현재 ①(프론트 Message 도메인 + `MockAdapter`)까지만.
