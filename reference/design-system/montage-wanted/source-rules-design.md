# rules/design.md — Montage(Wanted) 디자인 시스템 적용 규칙

> 출처: `_ds/montage-wanted-design-system/colors_and_type.css` + README
> 이 문서는 0.2(토큰), 1.2(공용 컴포넌트) 태스크의 바인딩 스펙이다. 여기 없는 값은 추측해서 만들지 말고 colors_and_type.css에서 확인한다.

## 1. 토큰 계층 — 2단 구조 그대로 이식

Montage는 **atomic → semantic** 2계층이다. `tokens.css`도 이 구조를 유지한다 (semantic만 임의로 하드코딩하지 말 것).

- **atomic**: 색상 램프 원값. 예) `--atomic-blue-50: #0066FF`, `--atomic-cn-10: #171719`, `--atomic-red-40/95`, `--atomic-orange-40/95`, `--atomic-green-40/95`
- **semantic**: 용도별 참조. 예) `--color-primary-normal`, `--color-label-normal/neutral/alternative`, `--color-bg-normal/alternative/elevated`, `--color-line-solid/normal`, `--color-status-positive/cautionary/negative`, `--color-fill-normal/alternative`
- **light/dark 둘 다** `:root`에 정의하고 `[data-theme="dark"]`로 스위치. semantic 값만 테마별로 바뀌고 atomic 값은 고정.

Tailwind theme에서는 hex를 복제하지 말고 `var(--color-*)`를 참조한다.

## 2. 컬러 — 이 프로젝트에서 실사용 중인 값

| 용도 | 토큰 | 값 |
|---|---|---|
| Primary / CTA | `--color-primary-normal` (`blue-50`) | `#0066FF` |
| 본문 텍스트 | `--color-label-normal` (`cn-10`) | `#171719` |
| 보조 텍스트 | `--color-label-neutral` | `rgba(55,56,60,.88)` |
| 3차 텍스트 | `--color-label-alternative` | `rgba(55,56,60,.61)` |
| Disabled 텍스트 | `--color-label-disable` | `rgba(55,56,60,.43)` |
| 카드/페이지 배경 | `--color-bg-normal` / `alternative` | `#FFFFFF` / `#F7F7F8` |
| 다크 elevated(토스트 등) | `--color-bg-elevated` (`cn-17`) | `#212225` |
| Modal dimmer | `--color-material-dimmer` | `rgba(23,23,25,.52)` |
| 미세 구분선 | `--color-line-normal` | `rgba(112,115,124,.08~.22)` |
| **CRITICAL** severity | `atomic-red-40` on `atomic-red-95` | `#E52222` on `#FEECEC` |
| **HIGH** severity | `atomic-orange-40` on `atomic-orange-95` | `#D47800` on `#FEF4E6` |
| **완료/positive** | `atomic-green-40` on `atomic-green-95` | `#009632` on `#D9FFE6` |
| 토스트 성공 아이콘 | `atomic-green-60` | `#1ED45A` |
| **승인 필요** 칩 | `blue-95` bg, `blue-50` text | `#EAF2FE` / `#0066FF` |

새 severity/상태색이 필요하면 반드시 `colors_and_type.css`의 기존 atomic 램프에서 짝(진한 텍스트 + 연한 배경, 40/95 페어링)으로 고른다. 임의 hex 금지.

## 3. 타이포그래피

- 폰트: Pretendard (CDN, dynamic subset) — 0.1/0.2 단계에서 반드시 로드
- 이모지 UI 사용 금지 — 아이콘은 wds-icon 대응 또는 자체 SVG(24×24, `fill=currentColor`)로 대체

## 4. 컴포넌트 규칙

- **명칭**: Badge가 아니라 **Chip**. 컴포넌트/스토리/테스트 이름을 Chip으로 통일.
- **라디우스**: 버튼 8/10/12px(사이즈별), Chip 6/8/10px, 카드 ~12px, Avatar 원형은 pill.
- **아웃라인 버튼/칩**: CSS `border` 대신 `inset 0 0 0 1px box-shadow` — 레이아웃 시프트 방지.
- **Disabled**: `label.disable` 텍스트 + `interaction.disable` 배경, `pointer-events:none`.
- **모션**: `0.2s ease` (칩은 `0.3s ease`) — 스프링/바운스 금지.
- **그림자**: neutral-tone, 6~12% opacity 5단계만 사용.
- **다크모드 표면**: normal `#1B1C1E`, elevated `#212225` — 커스텀 다크 배경 만들지 말 것.

## 5. Severity → Chip 색 규칙 테이블 (1.2 DoD "배지 색 규칙 테이블 테스트"의 근거)

| severity | 텍스트 | 배경 |
|---|---|---|
| CRITICAL | `#E52222` | `#FEECEC` |
| HIGH | `#D47800` | `#FEF4E6` |
| MEDIUM | `#9C5800`(`orange-30`) | `#FFFCF7`(`orange-99`) |
| 완료(승인/positive) | `#009632` | `#D9FFE6` |
| 승인 필요(정보) | `#0066FF` | `#EAF2FE` |

## 6. Montage에 없어서 자체 제작인 컴포넌트

BottomSheet, SafetyNotice, OfflineBanner, Skeleton, StepTimeline, 모바일 탭바 — Montage 라이브러리엔 없다. 위 토큰/규칙(라디우스, 아웃라인, 모션, 컬러 페어링)만 지켜서 새로 만들면 된다. 그 외 시각 요소를 임의로 발명하지 말 것.
