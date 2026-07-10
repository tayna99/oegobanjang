# 디자인 동기화 검수 — 외고반장 PC.dc.html (2026-07-11)

> 대상: claude.ai/design "Mobile screen design" 프로젝트(`bd0fd8f8-615f-48e9-875b-eb5c9e9b398d`)의 `외고반장 PC.dc.html`(+ 참고: `외고반장 Mobile.dc.html`)
> 질문: ① 디자인이 디자인 시스템과 동기화되어 토큰·컴포넌트를 잘 활용하는가 ② 어떤 디자인이 제품 목적에 제일 부합하는가
> 결론 요약은 §0, 마이그레이션 매핑표는 §3, 목적 부합 판단은 §5.

## 0. 결론 요약

1. **디자인 ↔ 디자인 프로젝트 내장 DS(Montage/Wanted): 정합 우수.** hex 색상 사용 674회 중 670회(99.4%)가 Montage 토큰 값과 정확히 일치하고, severity 색 페어·inset 아웃라인·그림자 체계·Pretendard·가드레일 고정 문구까지 프로젝트 규칙을 따른다.
2. **디자인 ↔ 저장소 구현(`src/styles/tokens.css`, prototype_v3 계열): 동기화 안 됨.** 저장소 토큰 값 13종이 디자인에 **0회** 등장. 공통은 `#0066FF`·Pretendard뿐이며 라디우스·그림자·모션·자간·다크모드·컴포넌트 명칭까지 체계가 다르다. 원인은 픽셀이 아니라 **스펙 분기** — 디자인 프로젝트에는 Montage 기반 개정판 `rules/design.md`·ROADMAP이 있었으나 저장소에 미반영 상태였다.
3. **목적 부합 1순위: "PC 통합 재설계"(3a 컨트롤 타워 · 3b 케이스 워크벤치 · 3c 거버넌스).** 단, 단계 도입 — 3b·3c 먼저, 3a는 M3(에이전틱) 이후. 근거는 §5.
4. **조치(이 브랜치에서 완료):** `rules/design.md`를 v2(Montage)로 교체, `plans/ROADMAP.md`에 M2.5 마일스톤 신설, `plans/HANDOFF.md`에 누락된 2.1 기록 이기. **별도 결정 필요:** CSV 업로드 화면(§4-7), 모바일 개편안 채택(§5-4).

## 1. 범위·방법·한계

- 파일 확보: DesignSync 읽기 API(`list_files`/`get_file`)로 디자인 프로젝트 원문을 가져와 정적 분석(색상·라디우스·폰트·그림자·자간 히스토그램, 저장소 토큰 값 교차 검색). 픽셀 단위 렌더링 대조는 수행하지 않음(추후 ui-matcher 몫).
- 분석 파일: `외고반장 PC.dc.html`(192KB — 내부에 디자인 3안 공존, §5), `외고반장 Mobile.dc.html`(헤더·구조만), 프로젝트 `rules/design.md`, `_ds/.../_ds_manifest.json`(토큰 전수), `uploads/ROADMAP.md`. `Montage 공용 컴포넌트.dc.html`은 이번 범위 밖(후속 검수 후보).
- 저장소 기준: `src/styles/tokens.css`, `rules/design.md`(v1), `src/components/{Button,Badge,Card}.tsx`, `tailwind.config.js`.
- 환경 한계: 이 세션 환경에는 Node가 없어 `npm run verify` 재실행 불가 — 이번 변경은 마크다운 문서 4건뿐이라 빌드·테스트에 영향 없음.

## 2. 디자인 ↔ Montage DS 정합 (양호)

**색상 — 사실상 전량 토큰 값.**

| 디자인 사용 값 | 회수 | 대응 토큰 |
|---|---|---|
| `#171719` | 205 | `--color-label-normal` (본문) |
| `#0066FF` | 131 | `--color-primary-normal` |
| `rgba(55,56,60,.61)` | 247 | `--color-label-alternative` (3차 텍스트) |
| `rgba(55,56,60,.88)` | 43 | `--color-label-neutral` (보조 텍스트) |
| `rgba(112,115,124,.08/.16/.22)` | 127/35/24 | `--color-fill-normal`/`-strong`/`--color-line-normal` |
| `#E52222` on `#FEECEC` | 24/14 | CRITICAL 페어 (red-40/95) |
| `#D47800` on `#FEF4E6` | 43/26 | HIGH 페어 (orange-40/95) |
| `#009632` on `#D9FFE6` | 31/12 | positive 페어 (green-40/95) |
| `#0066FF` on `#EAF2FE` | 45(bg) | 승인 필요 칩 (blue-50/95) |
| `#9C5800` on `#FFFCF7` | 4/2 | MEDIUM 페어 (orange-30/99) |
| `#4F29E5`/`#F0ECFE`, `#006F82`/`#DEFAFF` | 6/5, 5/4 | violet·cyan 램프 40(30)/95 페어 — "임의 hex 금지, 램프에서 페어로" 규칙 준수 |

- severity 색 페어가 프로젝트 `rules/design.md` §5 표와 **정확히 일치** (MEDIUM 포함).
- **아웃라인 = inset box-shadow** 규칙 준수: `inset 0 0 0 1px rgba(112,115,124,.22)` 24회 (CSS border 방식 아님 — 레이아웃 시프트 방지 규칙).
- 그림자: Montage 5단계 토큰 값 사용(`--shadow-medium` 8회 등). 변형 2건은 §4-6.
- 타이포: Pretendard(CDN dynamic subset), 이모지 UI 없음. 자간은 Montage `--ls-*` 계열(음수 자간) — §4-3의 근사값 이슈 있음.
- 가드레일 고정 문구 "승인 전에는 외부 발송이 차단됩니다." 3안 모두 존재(총 4회).
- 한계: `.dc.html` 캔버스 특성상 `var()`·클래스 참조는 0건(값을 인라인으로 하드코딩). 즉 동기화는 **값 기준**이며, 토큰 이름 변경·다크 테마 전환은 디자인에 자동 전파되지 않는다 — 구현 시에는 반드시 semantic 토큰 참조로 옮겨 적을 것.

## 3. 디자인 ↔ 저장소 구현 격차 (= M2.5 마이그레이션 매핑표)

저장소 토큰 값 교차 검색 결과: `#354153`(ink) `#f2f3f8`(surface) `#e5e8ef`(hairline) `#8b93a7`(muted) `#b4bbcb`(faint) `#EF4444` `#F97316` `#00913A` `#2563EB` `#B45309` `#6B7280` `#DC2626` `#EA580C` → **디자인 내 0회**.

### 3.1 토큰 매핑 (v3 → v2)

| 역할 | 저장소 v3 (`tokens.css`) | Montage v2 (semantic) | 디자인 사용(회) |
|---|---|---|---|
| 페이지·카드 배경 | `--canvas #ffffff` | `--color-bg-normal #FFFFFF` | 56 |
| 회색 서피스 | `--surface #f2f3f8` | `--color-bg-alternative #F7F7F8` | 19 |
| 짙은 서피스 | `--surface-dim #f5f5f5` | `--atomic-cn-97 #EAEBEC` (캔버스 배경) | 2 |
| 본문 텍스트 | `--ink #354153` | `--color-label-normal #171719` | 205 |
| 보조 텍스트 | `--muted #8b93a7` | `--color-label-neutral rgba(55,56,60,.88)` | 43 |
| 3차 텍스트 | (v3 없음 — muted 겸용) | `--color-label-alternative rgba(55,56,60,.61)` | 247 |
| 비활성·placeholder | `--faint #b4bbcb` | `--color-label-assistive .28` / `--color-label-disable .16` | 91 (단 .43 사용 — §4-4) |
| 구분선 | `--hairline #e5e8ef` | `--color-line-normal rgba(112,115,124,.22)` · `--color-line-solid-normal #E1E2E4` | 24 · 7 |
| 채움(fill) | (없음 — surface 겸용) | `--color-fill-normal rgba(112,115,124,.08)` 외 | 127+ |
| Primary / 눌림 | `--primary #0066FF` / `--primary-press #005EEB` | `--color-primary-normal` / `-strong` — **값 동일** | 131 / 0 |
| CRITICAL | `#EF4444` + 틴트 8% + 텍스트 `#DC2626` | `red-40 #E52222` on `red-95 #FEECEC` | 24·14 |
| HIGH(warning) | `#F97316` + 틴트 + `#EA580C` | `orange-40 #D47800` on `orange-95 #FEF4E6` | 43·26 |
| MEDIUM(pending) | `#B45309` + `--pendbg` | `orange-30 #9C5800` on `orange-99 #FFFCF7` | 4·2 |
| info(승인 필요) | `#2563EB` + `--infobg` | `blue-50 #0066FF` on `blue-95 #EAF2FE` | 45 |
| success | `#00913A` + `--succbg` | `green-40 #009632` on `green-95 #D9FFE6` | 31·12 |
| neutral | `#6B7280` + `--neutbg` | `cn-50 #70737C` on fill | 20 |
| 라디우스 | input 12 / chip·badge 14·8 / card 16 / sheet 20 | 버튼 8·10·12 / 칩 6·8·10 / 카드 ~12 / 아바타 pill | 5px 69 · 8px 63 · pill 55 · 10px 40 · 6px 38 (§4-2) |
| 그림자 | `--sh-card` 단일(+lift/sheet) | `--shadow-xsmall…xlarge` 5단계 + spread 2종 | medium 8 등 |
| 모션 | 150/240/360ms + cubic-bezier 2종 | 0.2s ease (칩 0.3s), 스프링 금지 | — |
| 자간 | `letter-spacing: normal` 강제 | `--ls-*` 스케일(음수~양수) | -0.023em 등 |
| 다크모드 | 없음 | `[data-theme="dark"]` semantic 전환 세트 | (라이트만 사용) |

### 3.2 컴포넌트 격차

| 컴포넌트 | 저장소 현행 | v2 규칙·디자인 | 전환(ROADMAP) |
|---|---|---|---|
| Badge | tone 7종, radius 8px, 틴트bg+진한 텍스트 (`src/components/Badge.tsx`) | **Chip**으로 개명, solid/outlined, radius 6/8/10, severity 색표(v2 규칙 §5) | 2.5.2 |
| Button | primary/secondary/**outline=CSS border** (`Button.tsx:16`), h 50/44, radius 12 | Solid/Outlined·Primary/Assistive·S/M/L, radius 8/10/12, outlined는 **inset box-shadow** | 2.5.2 |
| Card | hairline 보더 ↔ hero 단일 그림자(상호배타), radius 16 | radius ~12, 5단계 그림자 중 선택 | 2.5.2 |
| BottomSheet·SafetyNotice·OfflineBanner·Skeleton·StepTimeline·탭바 | 자체 제작 | Montage에 없음 — v2 토큰·규칙으로 유지(v2 규칙 §6) | 2.5.3 리스킨 |

### 3.3 레이아웃 격차

- 디자인: 1560px 데스크톱 캔버스, 3열 워크벤치·테이블 중심.
- 구현: 모바일 퍼스트 + `lg:` 상단 헤더 분기(`src/Shell.tsx`), 콘텐츠는 `max-w-screen-sm`(≈640px) 단일 칼럼. PC 전용 레이아웃 부재 → ROADMAP 2.5.4~2.5.6.

## 4. 디자인 내부 결함·수정 요청 목록 (디자인 프로젝트에 전달할 피드백)

| # | 항목 | 심각도 | 내용 |
|---|---|---|---|
| 4-1 | `#FAFAFB` 4회 | 낮음 | Montage 램프에 없는 임의값(cn-99 `#F7F7F8`·neutral-99 `#F7F7F7`와 별개). 램프 값으로 교체 요청 |
| 4-2 | 라디우스 4/5/7px | 낮음 | 규칙 스케일(6/8/10/12) 밖 미세 라디우스 113회. PC 밀도 적응으로 보이나 스케일 편입 또는 정리 필요 |
| 4-3 | 하프픽셀 폰트 | 중간 | 10.5/11.5/12.5/13.5px 등 타입 스케일 밖 크기 467회 — Montage `--fs-*`는 rem 기반 정수 스케일. PC 밀도용이면 **PC 전용 타입 램프를 토큰으로 승격**해야 구현이 따라갈 수 있음 |
| 4-4 | disabled 텍스트 `.43` | 중간 | 프로젝트 rules 문서와 디자인(91회)은 `rgba(55,56,60,.43)` 사용. `colors_and_type.css`에는 해당 라벨 토큰 없음(`assistive .28`/`disable .16`). **구현은 CSS 값을 따름** — rules v2 이식본에서 정정함, 디자인 측 확인 요청 |
| 4-5 | v1 캔버스 `{{ }}` 바인딩 90곳 | 정보 | "외고반장 PC v1" 안은 미해석 템플릿 바인딩이 노출되는 프로토타입 스캐폴드 — 시각 스펙으로 쓰지 말 것(아카이브 표시 권장) |
| 4-6 | 그림자 변형 2건 | 낮음 | `--shadow-large` 유사 값의 opacity 증폭 변형(.24/.28) — 토큰 값으로 회귀 요청 |
| 4-7 | **CSV 업로드 화면 부재** | 높음 | 통합설계 D4·D6, 데모 E4가 PC에 요구하는 "CSV 업로드"가 **3안 모두에 없음**. 온보딩(ROADMAP 4.1)과 연계해 화면 추가 결정 필요 |
| 4-8 | pill 55회 | 정보 | 규칙상 pill은 아바타 전용. 필터 칩 등에도 쓰였는지 시각 확인 필요(ui-matcher 몫) |

## 5. 목적 부합 판단

**판단 기준(스펙 근거):**
- `reference/specs/통합설계_v1.md:55` — "**모바일이 제품의 본체다.** … PC는 대량 데이터 관리와 정밀 검토를 위한 **확장 화면**", D4 "반응형 웹 단일", D6 "CSV 업로드(PC, 일괄)"
- `reference/specs/탭별_UXUI_상세기획_v1.md:186` — "감사 내보내기는 **PC 확장 화면 담당**"
- `reference/specs/8단계_데모시나리오_v1.md` E4 — PC 캡처 1장: "업무 큐 테이블·CSV 업로드·행정사 패키지"
- `reference/specs/9단계_에이전틱성_비판검토_v1.md` P0(=ROADMAP M3) — 프로액티브 런·런 체이닝의 가시화

**후보(모두 안1+안2+안3(모바일은 +안4) 레퍼런스의 종합안):**

| 후보 | 구성 | ①PC 위상(D4) | ②감사 내보내기 | ③데모 E4 | ④에이전틱 가시화 | ⑤재사용·리스크 | 판정 |
|---|---|---|---|---|---|---|---|
| **통합 재설계** (3a·3b·3c) | 컨트롤 타워(파이프라인 5단계·KPI 4종·우선 처리 큐)/워크벤치 3열/거버넌스(근거 라이브러리+감사 로그) | ◎ 3b=정밀 검토, 큐 테이블 | ◎ **유일하게 내보내기 포함** | ○ 큐 테이블 있음(CSV 없음) | ◎ 3a가 M3 파이프라인을 그대로 시각화 | ○ 범위 큼 → 단계 도입 필요 | **채택 (1순위)** |
| 운영 관제형 (2a~2d) | 3패널 브리핑/테이블+드로어/판단 기록/행정사 패키지 | ○ | △ 2c에 내보내기 언급 | ○ **2d 행정사 패키지 유일** | △ | ○ | 미채택 — **2d만 2.4 참조 스펙으로 승계** |
| PC v1 (S1~S5) | 앱 프레임+데이터 바인딩 | △ | △ | △ | △ | ◎ 현 구현과 유사 | 제외 — `{{ }}` 노출(§4-5), 시각 스펙 부적합 |
| Mobile 개편 (2a~2d) | 승인 큐 중심: 브리핑/사례 검토/최종 승인/승인 이력 | (본체 담당 — PC 비교 대상 아님) | — | — | ○ | △ 기구현 M1~M5 IA 변경 | **별도 결정** (§5-4) |

**권고: "통합 재설계"를 PC 방향으로 채택하되 단계 도입.**

1. **2.5.4 — 3b 케이스 워크벤치 먼저.** PC의 존재 이유(정밀 검토)를 직접 구현하고, 기구현 케이스 목록(2.1)·케이스 시트·스토어를 그대로 재사용할 수 있어 비용 대비 효과가 가장 크다.
2. **2.5.5 — 3c 거버넌스.** 탭별기획이 PC에 배정한 유일한 의무(감사 내보내기)를 이행. Evidence Log 제품 원칙(AGENTS §9)의 대외 증명 화면.
3. **2.5.6 — 3a 컨트롤 타워는 M3 완료 후.** 파이프라인 5단계·KPI·"에이전트 단계" 컬럼은 M3(프로액티브 런·런 체이닝) 데이터가 있어야 진짜가 된다. 먼저 만들면 목업 관제탑이 되고, "모바일이 본체" 원칙(D4)과의 긴장도 커진다. 데모 E4용 캡처는 3b+2d 조합으로도 충분.
4. **모바일 개편안(승인 큐 중심)은 가치 있으나 별도 결정.** "카드에서는 검토만, 승인은 체크리스트 화면에서"는 성급한 승인 방지(1.5 DoD 철학)를 강화하는 좋은 방향이지만, 완료된 M1~M5 화면의 IA 변경이므로 M2.5 리스킨과 묶어 진행할지 사용자 결정 필요.
5. 운영 관제형의 **2d 행정사 패키지**는 ROADMAP 2.4의 참조 스펙으로 지정(반영 완료) — 통합 재설계에는 행정사 패키지 화면이 없기 때문.

## 6. 조치 내역·후속

**이 브랜치에서 반영(문서 5건, src/ 변경 없음):**
- `rules/design.md` → v2(Montage) 교체. 이행 배너 + 현행 v3 부록 포함
- `plans/ROADMAP.md` → 디자인 기준 명시, M2.5 마일스톤(2.5.1~2.5.6) 신설, 2.4 스펙에 관제형 §2d 참조 추가
- `plans/HANDOFF.md` → 번들 사본에만 기록돼 있던 2.1 완료 엔트리 이기(원인: Codex 세션이 `외고반장_통합/13_.../plans/`에 기록)
- `docs/SPEC_INDEX.md` → 시각 기준 v1/v2 이원화 반영(prototype_v3=기구현 유지보수용, v2=신규·M2.5 기준)
- 본 보고서

**결정 완료(2026-07-11, 사용자 확정):**
- **PC 통합 재설계(3a·3b·3c) 채택** — ROADMAP M2.5로 확정. 단계 도입 순서(3b→3c→3a)는 §5 그대로.
- **4-3 PC 타입 램프 토큰화** — 임의값 방치 대신 `--fs-pc-*` 보조 스케일로 등록하기로 결정. `rules/design.md` §3, ROADMAP 2.5.1 DoD에 반영.
- **4-7 CSV 업로드 화면** — 부재를 방치하지 않고 ROADMAP **4.4**로 신설(온보딩 4.1과 데이터 계약 공유).
- **모바일 개편안(§5-4) 채택 여부** — **보류**. 근거: 현 M1~M5는 "스트리밍 완료 전 승인 disabled"(1.5 DoD)로 성급한 승인 방지를 이미 다른 방식으로 달성했고, `Mobile.dc.html`의 카드/승인 분리 IA는 이미 완료·E2E 테스트된 M1~M5 화면을 다시 짜야 해 비용이 크다. 재검토 조건: 파일럿에서 오승인(의도치 않은 승인) 사고가 실제로 발생하면 별도 태스크로 재론의.

**후속(별도 세션 — 아직 미결정):**
- §4 나머지 피드백(4-1 임의 hex, 4-2 라디우스, 4-6 그림자 변형)을 디자인 프로젝트에 전달
- `.claude/agents/ui-matcher.md` 기준을 prototype_v3 → 디자인 프로젝트로 교체(2.5.3에 포함, 이미 ROADMAP에 반영)
- `Montage 공용 컴포넌트.dc.html` 검수(이번 범위 밖)
- 2.2 이후 세션은 HANDOFF 규칙 준수 경로가 `plans/`(루트)임을 확인할 것
