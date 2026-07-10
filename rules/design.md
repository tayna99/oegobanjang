# rules/design — Montage(Wanted) 디자인 시스템 규칙 v2 (UI 작업 시 로드)

> **이행 상태(2026-07-11): 코드는 아직 v1(v3 토큰) 상태다.** 이 문서는 ROADMAP **M2.5**(디자인 시스템 v2 전환)의 바인딩 스펙이다.
> - 신규 화면·컴포넌트(2.2 이후, PC 화면 포함)는 **이 문서(v2)** 기준으로 작성한다.
> - 2.5.1~2.5.3 완료 전에 기존 화면을 손볼 때는 **부록 A(현행 v3 토큰)**를 따른다 — 한 화면에 두 체계를 섞지 말 것.
> 출처: claude.ai/design "Mobile screen design" 프로젝트 `rules/design.md` + `colors_and_type.css`(저장소 미러: `외고반장_통합/09_배포_패키지/외고반장_handoff_배포패키지_압축해제본/project/colors_and_type.css`).
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

## 6. Montage에 없어서 자체 제작인 컴포넌트

BottomSheet, SafetyNotice, OfflineBanner, Skeleton, StepTimeline, 모바일 탭바 — Montage 라이브러리엔 없다. 위 토큰/규칙(라디우스, 아웃라인, 모션, 컬러 페어링)만 지켜서 유지·리스킨한다. 그 외 시각 요소를 임의로 발명하지 말 것.

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

## 부록 A — 현행 v1(v3) 토큰 요약 (M2.5.3 완료 시 이 부록 삭제)

> 현재 `src/styles/tokens.css`가 실제로 담고 있는 값. 2.5.1~2.5.3 완료 전에 기존 화면을 수정할 때만 사용한다.
> 전체 스펙: `reference/specs/4단계_모바일디자인토큰_v1.md`, 시각 기준: `reference/prototype_v3.html`.

- 크롬: canvas `#fff` / surface `#f2f3f8` / ink `#354153`(검정 금지) / muted `#8b93a7` / faint `#b4bbcb`(placeholder 전용) / hairline `#e5e8ef`
- 브랜드: primary `#0066FF` — 화면당 CTA 1개 + 활성 탭 + 포커스 링 + 스파크 아이콘만
- 기능색: critical `#EF4444` / warning `#F97316` / pending `#B45309` / info `#2563EB` / success `#00913A` / neutral `#6B7280` — 배지·도트·상태 텍스트 전용, 배경은 8~10% 틴트 (배지 텍스트는 `--critical-text #DC2626`/`--warning-text #EA580C`)
- radius: input 12 / chip 14 / card 16 / sheet 상단 20 / badge 8. 필·직각 금지
- 그림자: 카드 `0 4px 8px rgba(0,0,0,.10)` 단일. hero 카드만 그림자(보더 없음), 나머지 hairline 보더 — 동시 사용 금지
- 모션: fast 150 / standard 240(시트) / slow 360(M5 push-in 전용). ease-enter `cubic-bezier(.2,0,0,1)`
- 타이포: Pretendard, **letter-spacing normal**. 화면타이틀 20/700, 인사문장 23/700, 카드제목 16/600, 본문 15/400, 라벨 14/600, 캡션 12~13, 숫자 tabular-nums. weight 900 금지
