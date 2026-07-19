# 디자인 시스템 원본 고정 (frozen 2026-07-11, 2026-07-13/07-17 갱신)

> **왜 이 폴더가 있는가**: M2.5 전환 전까지 저장소의 디자인 기준이 claude.ai/design "Mobile screen design" 프로젝트(`bd0fd8f8-615f-48e9-875b-eb5c9e9b398d`)라는 **외부 라이브 링크**에만 의존했다. 그 프로젝트가 수정·삭제되거나 접근 권한이 바뀌면 `rules/design.md`·`ROADMAP.md`(2.5.4~2.5.6)·`ui-matcher.md`가 가리키는 스펙이 통째로 사라진다. 이 폴더는 그 프로젝트에서 실제로 사용한 원본 파일을 **그대로, 재현 가능하게** 저장소에 고정한 것이다. 이후 디자인 결정에 대한 근거는 여기 파일을 1차로 삼는다.

## 내용물

| 파일 | 출처(프로젝트 내 경로) | 용도 |
|---|---|---|
| `montage-wanted/colors_and_type.css` | `_ds/montage-wanted-design-system-.../colors_and_type.css` | Montage(Wanted) 디자인 시스템의 원본 CSS 커스텀 프로퍼티. `src/styles/tokens.css`는 이 파일의 값을 그대로 이식한 것(§3 매핑표는 `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`). 저장소에 이미 있던 `외고반장_통합/09_배포_패키지/.../colors_and_type.css` 사본과 대조해 **내용 100% 일치**(줄바꿈 문자만 다름, sha256 비교로 확인) — 드리프트 없음.
| `montage-wanted/source-rules-design.md` | 프로젝트 `rules/design.md` | 디자인 프로젝트가 자체적으로 정의한 적용 규칙 원문. **이 저장소의 `rules/design.md`(v2)는 이 파일을 바탕으로 우리 프로젝트 규칙(부록·이행 배너 등)을 얹어 각색한 것**이다 — 원문과 각색본을 구분해 추적할 수 있게 둘 다 남긴다.
| `외고반장 PC.dc.html` | 프로젝트 루트 `외고반장 PC.dc.html` | PC 디자인 3안 원본(통합 재설계 3a·3b·3c / 운영 관제형 2a~2d / v1 프로토타입). ROADMAP **2.5.4~2.5.6**(PC 케이스 워크벤치·거버넌스·컨트롤 타워)의 1차 스펙 — 지금까지는 이 경로 없이 라이브 프로젝트만 가리켰다. `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` §5의 판단(통합 재설계 채택)이 바로 이 파일 내용에 근거한다. **이 파일 자체는 2026-07-13에 재수입하지 않았다** — 아래 `외고반장 PC_4a-4f(신규티어).dc.html` 항목 참고.
| `외고반장 PC_4a-4f(신규티어).dc.html` | 프로젝트 루트 `외고반장 PC.dc.html` (2026-07-13 재수입, **부분 캡처**) | 원격 프로젝트의 동일 파일이 역할 기반 신규 PC 화면 6종(4a 케이스 필터·정렬 테이블 / 4b 근로자 데이터 대량관리 / 4c 메시지 PC / 4d 발송 실행 큐 / 4e 행정사 패키지 뷰어 확장 / 4f 사장님 PC 최소화면)을 3a~3c/2a~2d/v1 **앞에 추가**하는 형태로 자랐다. `DesignSync get_file`은 256KiB에서 잘라 반환하므로(`truncated:true` 확인) **4a~4f 구간만 온전히 캡처**했고, 이어지는 3a~3c/2a~2d/v1 구간은 캡처하지 못해 파일 끝에 명시적 주석으로 표시했다 — 그 구간은 기존 `외고반장 PC.dc.html`(위 행)이 여전히 유효한 근거다(제목·섹션 헤더 텍스트 대조로 미변경 확인, 바이트 단위 대조는 아님). 4a~4f 델타 분류는 `docs/DESIGN_SYNC_AUDIT_2026-07-13.md` §3 참고.
| `외고반장 온보딩.dc.html` | 프로젝트 루트 `외고반장 온보딩.dc.html` (2026-07-13 신규) | 온보딩 O1~O5(전화인증·역할선택·사업장정보·첫근로자등록·첫브리핑생성) 원본. ROADMAP **4.1**의 1차 스펙. `reference/design-system/design-briefs/온보딩_O1-O5_브리프.md`를 claude.ai/design에 투입해 생성됨.
| `외고반장 CSV 업로드.dc.html` | 프로젝트 루트 `외고반장 CSV 업로드.dc.html` (2026-07-13 신규) | CSV 근로자 일괄 등록(PC) 원본. ROADMAP **4.4**의 1차 스펙. `reference/design-system/design-briefs/CSV_업로드_브리프.md`를 claude.ai/design에 투입해 생성됨.
| `외고반장 Mobile.dc.html` | 프로젝트 루트 `외고반장 Mobile.dc.html` | 모바일 개편안(승인 큐 중심) 원본. 최초 검수에서는 보류였으나 **2026-07-11 사용자 지시로 디자인 소스 채택 대상에 포함** — 채택 설계는 design-first 블루프린트 문서를 따른다.
| `Montage 공용 컴포넌트.dc.html` | 프로젝트 루트 `Montage 공용 컴포넌트.dc.html` | 자체 제작 컴포넌트 6종(모바일 탭바·BottomSheet·SafetyNotice 2종·OfflineBanner·Skeleton·StepTimeline)의 시각·모션 스펙 원본(2026-07-11 고정). `src/components/*`가 이 스펙과 정합해야 한다.
| `외고반장 알림 설정.dc.html` | 프로젝트 루트 `외고반장 알림 설정.dc.html` (2026-07-17 신규) | 설정 › 알림(A-3) 원본 — 알림카탈로그 §6 표 반영, 신규 pill 토글 스위치 채택. ROADMAP **R5.4 선행**의 1차 스펙. `reference/design-system/design-briefs/알림_설정_브리프.md`를 claude.ai/design에 투입해 생성됨. 감사: `docs/DESIGN_SYNC_AUDIT_2026-07-17.md`.
| `외고반장 서류 스캔 분류.dc.html` | 프로젝트 루트 `외고반장 서류 스캔 분류.dc.html` (2026-07-17 신규) | 서류 스캔 자동분류 확인(A-2) 원본 — 업로드→분류→매칭 확인·보정→확인 대기 반영 4단계 워크벤치(52px nav·290px 좌측 스텝트래커·340px 우측 안내 레일). ROADMAP **R5.2**의 1차 스펙. `reference/design-system/design-briefs/서류스캔_업로드_브리프.md`를 claude.ai/design에 투입해 생성됨. 감사: `docs/DESIGN_SYNC_AUDIT_2026-07-17.md`.
| `외고반장 근로자 응답 링크.dc.html` | 프로젝트 루트 `외고반장 근로자 응답 링크.dc.html` (2026-07-17 신규) | 근로자 응답 링크(A-1) 원본 — 무인증 모바일 단독 페이지, vi/ko 언어 토글 + 단일선택 프리셋 3종 + 자유입력. ROADMAP **R3.2** 프론트 절반의 1차 스펙. `reference/design-system/design-briefs/근로자_응답링크_브리프.md`를 claude.ai/design에 투입해 생성됨. 감사: `docs/DESIGN_SYNC_AUDIT_2026-07-17.md`.

온보딩·CSV 업로드는 **design-FILE-first**(고정 목업 존재)다 — `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md §9-B`에 따라 구현 화면은 이 절의 "System-derived" 태그를 붙이지 않고, PC §3b/§3c 화면들과 동일하게 소스 섹션을 인용하는 파일 상단 주석만 남긴다.

## System-derived 화면 (디자인 소스 없음)

`docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md` §9의 A등급("시스템 조립") 판정을 받아 목업 없이
지은 화면. 대조 기준은 목업이 아니라 `rules/design.md` v2 + 컴포넌트 킷 + 가장 가까운
채택 패턴(§9.1-A)이다 — §9.2가 요구하는 태깅을 여기 처음 실행한다.

| 화면 | 파일 | 재사용한 패턴 |
|---|---|---|
| M6 응답 해석 | `src/features/messages/ThreadPage.tsx` | 2b `CaseReviewPage` 구조 |
| M8 전역 판단 기록 | `src/features/governance/GlobalEvidencePage.tsx` | 2d `CaseHistoryPage` 타임라인 + PC §3c 감사 로그 행 |
| M9 런/재생 | `src/features/run/RunScreen.tsx`, `RunPage.tsx` | `StepTimeline` + 2.5.4b 재설계 |
| 커맨드바 | `src/features/briefing/CommandBar.tsx` | 홈 입력창 토큰 상속 |
| 설정 허브 | `src/features/settings/SettingsHubPage.tsx` | 행 관용구(CaseWorkbench) + 세그먼트 버튼(CASE_FILTERS) — 운영급 RBAC 확장(7단계 §6), PC 목업의 "설정" 네비 라벨은 순텍스트라 아이콘 발명 없음 |
| 구성원 관리 | `src/features/settings/MembersPage.tsx` | 행 관용구 + Chip(역할 배지는 상태 톤과 구분되게 neutral만) — 7단계 §5 |
| 위임 관리 | `src/features/settings/DelegationPage.tsx` | 행 관용구(대상 선택) + 원시 `<input type="date">`(새 시각 결정 아님) — 7단계 §3.1 |

## 고정 방식 · 한계

- claude.ai/design MCP(`DesignSync` 도구)의 `get_file`로 2026-07-11에 가져온 내용을 그대로 저장했다 — 사람이 손으로 편집하지 않았다.
- 이 파일들은 **읽기 전용 스냅샷**이다. 디자인 프로젝트가 이후 바뀌어도 여기는 자동으로 갱신되지 않는다 — 디자인이 실제로 바뀌면 다시 `get_file`로 받아 이 폴더를 갱신하고, 갱신 날짜와 무엇이 바뀌었는지를 이 README와 `plans/HANDOFF.md`에 남긴다.
- `.dc.html` 파일은 `<x-dc>` 캔버스 마크업(디자인 도구 전용 포맷)이라 브라우저에서 그대로 열어도 실제 프로덕션 렌더링과 다를 수 있다 — 값·구조 참고용이며, 실행 가능한 프로토타입은 아니다.
- `DesignSync get_file`은 응답을 256KiB에서 자른다(`truncated:true`). 원본 파일이 이보다 크면(2026-07-13 PC 재수입이 이 경우) 전체를 한 번에 가져올 수 없다 — 부분 캡처임을 파일명·이 표에 명시하고, 안 잘린 기존 스냅샷을 남겨둔 채 새 파일을 추가한다(기존 파일을 덮어써서 자른 채로 고정하지 않는다).

## 갱신 이력

- **2026-07-17**: 알림 설정(A-3)·서류 스캔 분류(A-2)·근로자 응답 링크(A-1) 신규 목업 3종 고정 — `plans/FRONTEND_DESIGN_TODO_2026-07-17.md`가 도출한 항목을 브리프화(`design-briefs/`)해 투입한 결과물. `get_file` 응답 전부 `truncated:false`(부분 캡처 없음). 감사 문서: `docs/DESIGN_SYNC_AUDIT_2026-07-17.md`.
- **2026-07-13**: 온보딩(신규)·CSV 업로드(신규) 목업 고정 + PC 재수입(부분, 4a~4f 델타만 캡처 — 위 표 참고). 감사 문서: `docs/DESIGN_SYNC_AUDIT_2026-07-13.md`.
- **2026-07-11**: 최초 고정(PC/Mobile/공용 컴포넌트/Montage 토큰/규칙 원문).
