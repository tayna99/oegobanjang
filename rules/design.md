# rules/design — Montage(Wanted) 디자인 시스템 규칙 v2 (UI 작업 시 로드)

> **이행 상태(2026-07-11 갱신): 2.5.1·2.5.2·2.5.3 완료.** `tokens.css`·`tailwind.config.js`·Chip(구 Badge)·Button 아웃라인·기존 화면 타이포그래피(heading1/heading2/body1/body2/label1/caption1)까지 전부 이 문서(v2) 기준으로 전환됐다 — 코드에 v1 hex·임시 타입 크기는 더 이상 없다. `.claude/agents/ui-matcher.md`도 이 프로젝트/문서를 기준으로 가리키도록 교체됨. 이 문서는 ROADMAP **M2.5**(디자인 시스템 v2 전환)의 바인딩 스펙이다.
> - PC 화면(2.5.4~2.5.6)은 이 문서를 그대로 기준으로 삼는다.
> 출처(고정본, 2026-07-11): `reference/design-system/montage-wanted/colors_and_type.css` + `source-rules-design.md` — claude.ai/design "Mobile screen design" 프로젝트에서 가져온 원본을 저장소에 재현 가능하게 고정한 사본이다(라이브 프로젝트가 바뀌거나 사라져도 이 문서의 근거는 유지된다). 고정 경위: `reference/design-system/README.md`.
> 정합 검수·마이그레이션 매핑표: `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` §3.

## 1. 토큰 계층 — 2단 구조 그대로 이식

Montage는 **atomic → semantic** 2계층이다. `tokens.css`(v2)도 이 구조를 유지한다 (semantic만 임의로 하드코딩하지 말 것).

- **atomic**: 색상 램프 원값. 예) `--atomic-blue-50: #0066FF`, `--atomic-cn-10: #171719`, `--atomic-red-40/95`, `--atomic-orange-40/95`, `--atomic-green-40/95`
- **semantic**: 용도별 참조. 예) `--color-primary-normal`, `--color-label-normal/neutral/alternative`, `--color-bg-normal/alternative/elevated`, `--color-line-solid/normal`, `--color-status-positive/cautionary/negative`, `--color-fill-normal/alternative`
- **light/dark 둘 다** 정의한다. 원본 CSS는 `[data-theme="light"]`/`[data-theme="dark"]` 셀렉터에 semantic을 정의한다(기본 라이트) — 이식 시 동일 구조를 유지하고 `[data-theme="dark"]`로 스위치. semantic 값만 테마별로 바뀌고 atomic 값은 고정.

Tailwind theme에서는 hex를 복제하지 말고 `var(--color-*)`를 참조한다.

## 2. 컬러 — 이 프로젝트에서 실사용 중인 값

| 용도 | 토큰 | 값 |
|---|---|---|
| Primary / CTA | `--color-primary-normal` (`blue-50`) | `#0066FF` |
| 본문 텍스트 | `--color-label-normal` (`cn-10`) | `#171719` |
| 보조 텍스트 | `--color-label-neutral` | `rgba(55,56,60,.88)` |
| 3차 텍스트 | `--color-label-alternative` | `rgba(55,56,60,.61)` |
| 힌트 텍스트 | `--color-label-assistive` | `rgba(55,56,60,.28)` |
| Disabled 텍스트 | `--color-label-disable` | `rgba(55,56,60,.16)` ¹ |
| 카드/페이지 배경 | `--color-bg-normal` / `alternative` | `#FFFFFF` / `#F7F7F8` |
| 다크 elevated(토스트 등) | `--color-bg-elevated` (`cn-17`) | `#212225` |
| Modal dimmer | `--color-material-dimmer` | `rgba(23,23,25,.52)` |
| 미세 구분선 | `--color-line-normal` 계열 | `rgba(112,115,124,.08~.22)` |
| **CRITICAL** severity | `atomic-red-40` on `atomic-red-95` | `#E52222` on `#FEECEC` |
| **HIGH** severity | `atomic-orange-40` on `atomic-orange-95` | `#D47800` on `#FEF4E6` |
| **완료/positive** | `atomic-green-40` on `atomic-green-95` | `#009632` on `#D9FFE6` |
| 토스트 성공 아이콘 | `atomic-green-60` | `#1ED45A` |
| **승인 필요** 칩 | `blue-95` bg, `blue-50` text | `#EAF2FE` / `#0066FF` |

¹ 디자인 프로젝트 원문 표는 disable을 `.43`으로 적었고 PC 디자인도 `.43`을 사용했으나, `colors_and_type.css`에는 `.43` 라벨 토큰이 없다(assistive `.28` / disable `.16`). **구현은 CSS 토큰 값을 따른다.** 디자인 측 정정 요청: AUDIT §4-4.

새 severity/상태색이 필요하면 반드시 `colors_and_type.css`의 기존 atomic 램프에서 짝(진한 텍스트 + 연한 배경, 40/95 페어링)으로 고른다. 임의 hex 금지.

## 3. 타이포그래피

- 폰트: Pretendard (CDN, dynamic subset) — 토큰 단계에서 반드시 로드
- 크기·자간은 `--fs-*`/`--lh-*`/`--ls-*` 스케일 사용 (v1의 "letter-spacing normal 강제"는 v2에서 폐기 — Montage 자간 토큰을 따른다)
- **PC 밀도 타입램프(결정 2026-07-11):** `외고반장 PC.dc.html`은 `--fs-*` 표준 스케일 밖의 하프픽셀 크기(10.5/11.5/12.5/13.5px 등, 총 467회)를 광범위하게 쓴다. 이를 임의값으로 방치하지 않고 `--fs-pc-*` 보조 스케일로 토큰 등록한다(2.5.1 DoD). 모바일 화면에는 적용하지 않는다.
- 이모지 UI 사용 금지 — 아이콘은 wds-icon 대응 또는 자체 SVG(24×24, `fill=currentColor`)로 대체

## 4. 컴포넌트 규칙

- **명칭**: Badge가 아니라 **Chip**. 컴포넌트/스토리/테스트 이름을 Chip으로 통일 (M2.5.2에서 개명).
- **라디우스**: 버튼 8/10/12px(사이즈별), Chip 6/8/10px, 카드 ~12px, Avatar 원형은 pill. (pill은 아바타 전용 — 칩에 쓰지 않는다)
- **아웃라인 버튼/칩**: CSS `border` 대신 `inset 0 0 0 1px box-shadow` — 레이아웃 시프트 방지.
- **Disabled**: `label.disable` 텍스트 + `interaction.disable` 배경, `pointer-events:none`.
- **모션**: `0.2s ease` (칩은 `0.3s ease`) — 스프링/바운스 금지.
- **그림자**: neutral-tone, 6~12% opacity 5단계(`--shadow-xsmall…xlarge`)만 사용.
- **다크모드 표면**: normal `#1B1C1E`, elevated `#212225` — 커스텀 다크 배경 만들지 말 것.

## 5. Severity → Chip 색 규칙 테이블 (2.5.2 DoD "Chip 색 규칙 테이블 테스트"의 근거)

| severity | 텍스트 | 배경 |
|---|---|---|
| CRITICAL | `#E52222` | `#FEECEC` |
| HIGH | `#D47800` | `#FEF4E6` |
| MEDIUM | `#9C5800`(`orange-30`) | `#FFFCF7`(`orange-99`) |
| 완료(승인/positive) | `#009632` | `#D9FFE6` |
| 승인 필요(정보) | `#0066FF` | `#EAF2FE` |
| 초안 생성(파이프라인) | `#4F29E5` | `#F0ECFE` |
| 감지(파이프라인) | `#006F82` | `#DEFAFF` |

파이프라인 2행은 2.5.4b에서 추가(디자인 §3a/§2a — Montage 램프 밖 프로젝트 확장, `--chip-draft-*`/`--chip-detected-*`). 근거 등급에 **F(합성 데이터)** 가 추가됐다 — **F등급은 근거로 사용 불가**(§3c 각주 비준, `usableCitations`가 citation-0 잠금 판정에서 제외).

## 6. Montage에 없어서 자체 제작인 컴포넌트

BottomSheet, SafetyNotice, OfflineBanner, Skeleton, StepTimeline, 모바일 탭바 — 시각·모션 스펙의 원본은 `reference/design-system/Montage 공용 컴포넌트.dc.html`(2026-07-11 고정)이며 2.5.4b에서 전부 정합 완료:
- **SafetyNotice 2형** — neutral(고정 문구 전용, children 불가) / emphasis(오렌지 경고, 상황 문구)
- **OfflineBanner 경고형** — orange-95 배경 + "오프라인 상태입니다 · 재연결 시 자동 동기화" + 재시도 링크(onRetry 있을 때만)
- **Skeleton shimmer** — fill 토큰 그라데이션 1.6s ease(reduced-motion 정지), 기하 유지
- **StepTimeline 세로형** — done=초록 체크 원 / streaming 마지막=파랑 펄스 링(step-ring) / 가드레일=경고 톤 칩·라벨(숨김 금지)
- **탭바** — 활성 primary / 비활성 label.alternative(.61), 아이콘: 브리핑=문서형·케이스=폴더·기록=시계
- **Toggle(pill 스위치, 2026-07-17)** — `src/components/Toggle.tsx`. 온보딩 O1(StepPhoneAuth
  "본인확인 사용")에 있던 마크업을 알림 설정 화면 신설 계기로 공용화했다. 트랙 h-6 w-11(24×44px,
  ON=`bg-primary`/OFF=`bg-track`), 노브 size-5(20×20px) `bg-white shadow-lift`
  `translate-x-0.5`↔`translate-x-5`, `transition duration-btn ease-v2`. **잠금(locked) 변형** —
  항상 ON이고 끌 수 없는 항목(예: "승인 요청 즉시 알림") 전용, 트랙 `bg-toggleLocked`
  (`--toggle-locked-bg`, primary 35% — Montage 램프 밖 확장) + 노브 안에 `IconLock` 10px,
  `disabled` 처리(클릭 무반응).
그 외 시각 요소를 임의로 발명하지 말 것.

## 7. 상태 표현 (v1에서 승계 — 디자인 시스템 독립 규칙)

- 스켈레톤: line/fill 계열 토큰 블록, 기하 유지, 수치는 `--`
- 비활성 CTA: `interaction.disable` 배경 + `label.disable` 라벨 (기하 불변)
- 빈 상태: 문장 1 + 행동 1. 일러스트·이모지 금지
- 성공(소액): 하단 3초 다크 토스트(`bg-elevated`) / 승인 완료: 전용 화면(M5), 토스트 금지

## 8. 카피 (v1에서 승계 — 변경 금지)

- 고정 문구: "승인 전에는 외부 발송이 차단됩니다." (변경 불가)
- CTA 명령형 동사, 단정·느낌표·이모지 금지, 에러는 원인 1줄+행동 1개
- 마이크로카피는 스펙(탭별기획)의 문장을 그대로 복사 — 창작 금지

---

> 부록 A(v1/v3 토큰 요약)는 2.5.1·2.5.2 완료(2026-07-11)로 코드에서 실제로 사라져 삭제했다.
> v1 값이 궁금하면 git 이력의 이 시점 이전 커밋을 참고한다.
