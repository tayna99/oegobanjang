# ROADMAP — 마일스톤 · 태스크 스펙 · DoD

> 태스크 1개 = Claude Code 세션 1개 크기. 순서대로. 각 태스크: 위임 레벨(L1 자율 / L2 계획 승인 / L3 협업) + 읽을 스펙 + DoD(검증 명령).
> 진행 기록은 `plans/HANDOFF.md`에 남긴다 (에이전트가 태스크 종료 시 갱신).
> 디자인 기준(2026-07-11 확정): claude.ai/design "Mobile screen design" 프로젝트의 **Montage(Wanted) 시스템** — `rules/design.md`(v2)와 `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` 참조. 전환 작업은 M2.5.

## M0 — Sanity 기반 (코드보다 검증 먼저)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 0.1 | Vite+React+TS+Tailwind+router+zustand 스캐폴드, `npm run verify` 스크립트 구성 | L1 | — | `verify` 통과, 빈 앱 렌더 |
| ✅ 0.2 | `styles/tokens.css` + tailwind theme 연동 (v3 `:root` 이식) | L1 | prototype_v3, rules/design.md | 토큰 스냅샷 테스트 1개 |
| ✅ 0.3 | `src/types.ts` 데이터 타입 + `calcDday`·`maskId` 유틸 + 단위 테스트 | L1 | 1단계 §0.4 | dDay 경계값(D+, D-0, D-30, D-90) 테스트 통과 |
| ✅ 0.4 | 스토어 3종(case/approval/evidence) + **가드레일 테스트** | L2 | GOTCHAS §1·2 | "승인 없이 dispatch 불가"·"evidence append-only"·"중복 승인 차단" 테스트 통과 |
| ✅ 0.5 | mocks 이식 (v3의 CASE/DRAFT/APPROVE/EV → fixtures) | L1 | SPEC_INDEX 이식표 | typecheck 통과, PII 원문 없음 검사 |

## M1 — 셸과 승인 해피패스 (데모 3막의 뼈대)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 1.1 | 라우터+딥링크 맵, Shell(모바일 탭바/PC 헤더 분기) | L2 | 2단계 §3, 탭별기획 §0 | 라우트 스냅샷 테스트, 딥링크 백스택 = M1→목적지 |
| ✅ 1.2 | 공용 컴포넌트: Button/Badge/Card/SafetyNotice/OfflineBanner/Skeleton | L1 | 1단계 §0.2·0.3, rules/design.md | 스토리 렌더 테스트, 배지 색 규칙 테이블 테스트 (Badge는 이후 M2.5.2에서 Chip으로 개명) |
| ✅ 1.3 | M1 브리핑 홈 (5상태 전부: default/empty/loading/error/offline) | L2 | 1단계 M1, 탭별기획 §1 | 상태별 렌더 테스트 5개, empty에 온보딩 유도 |
| ✅ 1.4 | BottomSheet + M2 케이스 시트 (데이터 구동, 케이스별 복제 금지) | L2 | 1단계 M2, GOTCHAS §4 | citation 0건 → 승인 locked 테스트 |
| ✅ 1.5 | 런 엔진 + StepTimeline (mode: approval/command/replay, 스텝 스트리밍) | **L3** | 1단계 M9 v1.2, ARCHITECTURE §5 | 스트리밍 완료 전 승인 disabled 테스트, guardrail 스텝 렌더 |
| ✅ 1.6 | M3 초안(언어 토글·수정 요청 시트) + M4 승인 + M5 완료 + 상태 전파 | L2 | 1단계 M3~M5 | **E2E: 알림딥링크→M1→M2→M3→M4→M5→M1 상태 반영** (playwright) |

## M2 — 나머지 탭 (확인 면)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 2.1 | M7 케이스 목록 (필터 칩·그룹·딥링크 프리셋) | L1 | 1단계 M7, 탭별기획 §2 | 필터·정렬 deterministic 테스트 |
| ✅ 2.2 | 메시지 탭 + 스레드 대화 뷰 + M6 응답 해석(isFinal:false→확인) — 목록 원문 미노출, 원문은 스레드 내부만. main 병합(2026-07-16) 후 정본은 `threadStore`/`mocks/threads.ts` 기반 구현(`features/messages/MessagesScreen.tsx`, `features/thread/*`) — PC 4c(`MessagesWorkbench`)는 별도 mock(`mocks/messages.ts`)을 쓰는 독립 데스크톱 화면으로 그 위에 병존 | L2 | 1단계 M6, 탭별기획 §3, 블루프린트 §9-A | 해석 확인 시 상태 갱신+evidence 테스트 |
| ✅ 2.3 | M8 판단 기록 (타임라인·필터·이벤트 상세 시트·딥링크 하이라이트) — 모바일 /evidence, audit.ts 재사용 | L1 | 1단계 M8, 탭별기획 §4 | 해시만 표시(원문 없음) 테스트 |
| ✅ 2.4 | 행정사 패키지 화면 — 대상 케이스 Batbayar(블루프린트 §3 로스터), 포함 항목 토글·검토 요청서·PII 마스킹·승인 게이트 내보내기+이력 | L1 | PC.dc.html 운영관제형 §2d, 블루프린트 §1 | 승인 흐름 단계 렌더 테스트, 내보내기 승인 게이트 테스트 |

## M2.5 — 디자인 시스템 v2(Montage) 전환 · PC 확장 화면

> 근거: `reference/design-system/외고반장 PC.dc.html`(저장소에 고정된 사본, 원본은 claude.ai/design `bd0fd8f8-615f-48e9-875b-eb5c9e9b398d` — 고정 경위는 `reference/design-system/README.md`)의 **통합 재설계(3a·3b·3c) — 사용자 확정(2026-07-11)** + `rules/design.md`(v2) + `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`(매핑표 §3, 판단 §5).
> 순서: 2.2~2.4 착수 전에 2.5.1~2.5.3을 먼저 끝내는 것을 권장(신규 탭을 v2 토큰으로 바로 구현해 이중 리스킨 방지). 2.5.6은 M3 완료 후.
> 결정(2026-07-11): CSV 업로드 화면 → **4.4로 신설**(아래 M4 표). 모바일 개편안(`reference/design-system/외고반장 Mobile.dc.html` 승인 큐 중심) → **보류, M2.5 범위 밖**(사유: AUDIT §5-4).

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 2.5.1 | tokens.css v2 — Montage atomic+semantic 2계층·light/dark(`[data-theme="dark"]`) 이식, Tailwind theme `var(--color-*)` 재배선, PC 밀도 타입램프(10.5~13.5px) 토큰 등록 | L1 | rules/design.md(v2) §1·2·3, colors_and_type.css | 토큰 스냅샷 갱신, 다크 테마 스위치 렌더 테스트, Pretendard 로드 확인, PC 타입램프 임의값 0건 |
| ✅ 2.5.2 | 공용 컴포넌트 v2 — Badge→Chip 개명·severity 색표 교체, Button/Card 라디우스·아웃라인(inset box-shadow)·모션(0.2s ease) 전환 | L2 | rules/design.md(v2) §4·5 | Chip severity 색 규칙 테이블 테스트, 아웃라인 inset box-shadow 스냅샷, 기존 테스트 전건 통과 |
| ✅ 2.5.3 | 기구현 화면(M1 전체·2.1 케이스 목록) v2 리스킨 + ui-matcher 기준을 디자인 프로젝트로 교체 + rules/design.md 부록 A 삭제 | L2 | AUDIT §3 매핑표 | 1.6 E2E 통과, verify PASS, 임의 hex 0건(verifier grep) |
| ✅ 2.5.4 | PC 케이스 워크벤치(3b, 3열: 목록·상세·AI 패널) — Shell lg+ 레이아웃 확장, 기존 라우트·스토어 재사용 | L2 | `reference/design-system/외고반장 PC.dc.html` §3b, 탭별기획 §2 | 3열 렌더·목록↔상세 동기 테스트, 모바일 회귀 없음 |
| ✅ 2.5.4b | **Design-first 파운데이션** — 6인 로스터 치환·모델 확장(team/담당/caseCode/체류만료/근거 완성도/agentStage)·중앙 citationStore(id·status·F등급)·EvidenceType 3종(+해시 시드 #4783~91)·토큰 2쌍(draft 보라/detected 시안)+.43 계층·컴포넌트 킷 6종 정합 | L2 | 블루프린트 §3·§4, `Montage 공용 컴포넌트.dc.html` | 기존 테스트 전건(로스터 반영 개정), returned 전이·케이스 단위 승인·F등급 사용 불가 가드레일 테스트, Chip draft/detected 색표 테스트 |
| ✅ 2.5.5 | PC 거버넌스(3c) — 근거 라이브러리(중앙 스토어·KPI 파생·연계 케이스·F등급)·감사 로그(필터·해시·INSERT-only) | L2 | `외고반장 PC.dc.html` §3c, 탭별기획 §4, 블루프린트 §3 — **선행: 2.5.4b** | 내보내기 산출물 해시만(원문 없음) 테스트, 라이브러리 KPI=스토어 파생값 |
| ✅ 2.5.6 | PC 컨트롤 타워(3a) — 파이프라인·KPI·우선 처리 큐·활동/감사 레일 (파이프라인 델타·주간 추이는 mock, 실집계는 M3 데이터로 교체) | L3 | `외고반장 PC.dc.html` §3a, 9단계 P0, 블루프린트 §2(C10: 고위험 행 액션은 "검토") | 큐 정렬(위험×D-day) deterministic 테스트, KPI=스토어 파생값 |

## M2.6 — 모바일 승인 큐 개편 (Mobile.dc.html 2a~2d 채택)

> 근거: `reference/design-system/외고반장 Mobile.dc.html` + `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md`(§1 채택 맵·§2 교정 3건·§5 라우팅). 2026-07-11 사용자 지시로 기존 '보류'를 대체. **선행: 2.5.4b.**
> 데모 대본(8단계 3막) 개정 필요 — 스트리밍 게이트 → 체크리스트 게이트(블루프린트 §2). 사용자 확인 항목.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 2.6.1 | M1 브리핑 홈 개편(2a): 파이프라인 스탯 로우·"내가 처리할 승인 N건" 카드(단일 "검토" CTA)·"에이전트 진행 중" 리스트 — 커맨드바 존치 | L2 | Mobile.dc.html §2a, 블루프린트 §1 | 2a 카피 렌더 테스트, 카드 CTA 1개 테스트, 기존 5상태 테스트 개정 통과 |
| ✅ 2.6.2 | 케이스 상세 전면 페이지(2b): 바텀시트 대체 — 왜 확인·누락 서류·연결 근거·초안 VN/KR·"검토 계속" | L2 | Mobile.dc.html §2b | 전면 페이지 렌더, 검토 계속→승인 페이지 이동 테스트, PC 워크벤치 회귀 없음 |
| ✅ 2.6.3 | 승인 체크리스트 페이지(2c): 필수 4항목 게이트·의견/반려 사유·승인/반려(returned 전이) — 배너 문구는 정본 교정(C1) | L2 | Mobile.dc.html §2c, 블루프린트 §2 | 체크리스트 미완 시 승인 disabled, citation-0 잠금 유지, 반려 사유 evidence 기록 테스트, E2E(1.6) 개편 흐름 갱신 |
| ✅ 2.6.4 | 승인 이력 페이지(2d): `/case/:id/history` 신설 — 6노드 타임라인·해시·소요시간, 노드 색은 §4.2 정본(C9: 사람 결정만 primary) | L2 | Mobile.dc.html §2d, 탭별기획 §4.2 | 사람 결정 노드만 primary 테스트, 해시만 표시(원문 없음) 테스트 |

## M3 — 에이전틱 차별화 (9단계 P0)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 3.1 | 프로액티브 런: 이벤트→자동 런→카드 `preparedBy:'agent'`+재생 뷰 | **L3** | 9단계 P0-1, 1단계 v1.2 | 재생 뷰 읽기 전용, 가드레일 정지 스텝 존재 테스트 (재생 #4788에 발송 전 정지 스텝 추가) |
| ✅ 3.2 | 커맨드 바 → M9 사용자 런 → 결과 카드 → 케이스 연결 | L2 | 1단계 M9 | 런 1건=evidence 1건 테스트 (결과 카드 처리 대상 케이스→nav.toCase) |
| ✅ 3.3 | 케이스 에이전트 활동 타임라인(런 체이닝)+nextWake | L2 | 9단계 P0-2 | 체인 렌더 테스트 (타임라인 판단 기록 #→재생 런 진입) |
| ✅ 3.4 | 데모 폴리시: 8단계 4막 대본 그대로 시연 가능 상태 점검 | L1 | 8단계 | 데모 체크리스트 전 항목 수동 확인 + E2E 스모크 (demoScript.test 4막 스모크 + 커맨드 런 가드레일 스텝 추가) |

## M4 — 온보딩·권한 (파일럿 준비)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 4.1 | 온보딩 O1~O5 (수기 4필드 → 첫 브리핑 동기 생성 연출) | L2 | 3단계 | E2E: 근로자 1명 등록→첫 카드 도달 — `src/features/onboarding/OnboardingFlow.tsx`(Shell 바깥 형제 라우트 `/onboarding`), `lib/onboarding.ts`(완료 시 로스터 시드+evidence) |
| ✅ 4.2 | 역할 분기(owner/manager 홈·권한 가드) | L2 | 7단계 §2·6 | 라우트 가드 테스트 (owner의 M9 쓰기 도구 차단) — roleStore + Shell 토글, visibleCardsForRole 연결, RunPage 라우트 가드 |
| ✅ 4.3 | 승인 본인확인 목업(PIN) + 대리 승인 배지 | L2 | 7단계 §3·4 | 승인 이벤트에 결정자·본인/대리 기록 — ApprovePage PIN 시트(고정 데모값+불일치 재시도) + 대리 체크박스, evidence actor "OO (본인 확인 완료)"/"OO (대리 승인 · 위임: 김대표)" |
| ✅ 4.4 | CSV 일괄 업로드(PC) — 근로자 대량 등록, 4.1 온보딩과 동일 데이터 계약 공유 | L2 | 통합설계 D4·D6, 8단계 E4 | 잘못된 행(헤더 누락·중복 사번) 검증 실패 테스트, 성공 시 근로자 N명 스토어 반영 테스트 — `lib/csvUpload.ts`(validateRows/rowsToCards), `CsvUploadPage`/`CsvUploadWorkbench`(`/cases/import`, 담당자 전용), CaseWorkbench 좌측 레일 진입 버튼 |

## ✅ 4.2/4.3 확장 — 운영급 RBAC(7단계 권한모델·승인위임 전체)

4.2/4.3의 MVP 축소판(owner/manager 2역할, 체크박스식 대리) 이후 사용자 지시로
`reference/specs/7단계_권한모델_승인위임_v1.md` 전체를 구현했다. **목업 없이 진행** —
근거는 3개 Explore + 1개 Plan 에이전트가 실제 파일(PC/Mobile .dc.html, 기존 컴포넌트)을
대조 검증: 설정/구성원/위임/정책 화면은 전부 기존 채택 패턴(행 목록·세그먼트 버튼·체크박스)
으로 조립 가능했고, 행정사 링크는 이미 얼어붙은 PC §2d 콘텐츠의 상태 확장이었다
(블루프린트 §9.1-A와 동일 논리 — 자세한 판단 근거는 Phase A~D 커밋 메시지 참조).

| Phase | 내용 | 커밋 |
|---|---|---|
| A | Role 3종(manager/owner/viewer) + EvidenceType 9종(§5) + CompanyMember/DelegationConfig/ApprovalPolicy + companyStore + M8 역할 라벨 접두 | f4258eb |
| B | 기존 화면(M1~M4) 역할 매트릭스 반영 — owner 통계 숨김·M2 액션바 분기·정책 기반 "대표 승인 요청"·공동대표 배너·viewer 라우트 가드 | 166360f |
| C | 설정 화면 3종 신설(구성원 관리·위임 관리·승인 정책), system-derived 태깅 첫 실행(기존 M6/M8/M9/커맨드바도 backfill) | 174a0ec |
| D | 행정사 패키지 링크 만료(7일)·재발급·열람 로그 + 무인증 라우트(`/link/:packageId`) + 자동 에스컬레이션 프리시드("승인 지연" Chip) | 7de28f7 |

**의도적으로 다루지 않은 것**(스펙 §7 "미해결 → 후속"과 동일 — 후속 파일럿 피드백 이후):
- viewer의 M8 PII 마스킹 수준 차등, 승인 정책 케이스유형별 세분화(파일럿/운영 데이터 후).
- ✅ **expert 화이트라벨 모드** — 2026-07-14 설계+동작 목업 완료(아래 M4.6). 실 인증·백엔드만 후속.
- 공동대표 배너는 메커니즘 구현+테스트 완료(Phase B)이나, 6인 활성 로스터를 건드리는
  영구 프리셋 케이스는 추가하지 않음(기존 승인 대기 카운트 테스트·8단계 데모 대본 보존).
- 48h/72h 실시간 에스컬레이션 타이머 — 백엔드·다중 세션이 없어 물리적으로 불가능,
  RunEngine 각본 철학과 동일하게 프리시드 evidence로 대체.
- companyStore.approvalPolicy 기본값은 스펙상 "정답"인 owner_only 대신 manager_allowed —
  owner_only를 기본값으로 두면 이미 확립된 8단계 데모 대본·approvalFlow.test.tsx 대부분이
  즉시 "대표 승인 요청"으로 바뀌어 깨진다(설정 화면에서 owner_only로 전환해 그 분기 시연 가능).

## M4.5 — 온보딩·CSV 목업 확보 + PC 역할 기반 신규 화면(2026-07-13)

4.1(온보딩)·4.4(CSV)는 B-tier(design-then-freeze)로 목업 없이는 블록 상태였다(브리프는
`reference/design-system/design-briefs/`에 선작성). 2026-07-13, 사용자가 두 브리프를
claude.ai/design에 투입해 목업을 생성하고 `외고반장 PC.dc.html`도 재수입 — 재수입판은
역할 기반 신규 PC 화면 6종(4a~4f)을 기존 3a~3c/2a~2d/v1 앞에 추가한 형태였다. 감사:
`docs/DESIGN_SYNC_AUDIT_2026-07-13.md`(정합 우수, 마스킹 형식 1건 불일치 — 전체 마스킹
유지로 확정). 사용자 결정으로 **4a~4f 신규 PC 화면까지 이번 스코프에 전부 포함**한다.

| # | 태스크 | 분류 | 근거·비고 |
|---|---|---|---|
| ✅ 4.1 | 온보딩 O1~O5 | 완료 | 목업: `외고반장 온보딩.dc.html`. 단일 상태머신 컴포넌트(6단계) + Shell 바깥 형제 라우트. 외국인등록번호는 목업의 부분 마스킹 대신 `maskId()` 전체 마스킹 채택(§2 결함 판정). |
| ✅ 4.4 | CSV 일괄 업로드 | 완료 | 목업: `외고반장 CSV 업로드.dc.html`. 실제 Shell 크롬(64px) 위 4단계(대기→검증→결과→완료), 외국인등록번호는 전체 마스킹(목업의 부분 마스킹 미채택). |
| ✅ 4.5a | PC 케이스 테이블 보강(4a) | 부분 확장 완료 | `CaseWorkbench.tsx` 목록 행에 담당·서류 준비율(N/M) 노출 추가. **프리셋 필터 5종은 미채택** — 기존 `CASE_FILTERS`(전체/즉시확인/우선확인/확인필요/승인대기)가 모바일 `CaseListScreen`과 공유돼 교체 시 파급 범위가 크고 별도 IA 결정이 필요해 이번 스코프에서 제외(§3 델타표에 이미 명시된 "부분" 범위). |
| ✅ 4.5b | PC 근로자 데이터 관리(4b) | 순신규 완료 | `/cases/workers`(담당자 전용) — 근로자 목록(workerRef 있는 CaseCard 전체, 워커 전용 엔티티 없음) + CSV 가져오기 진입점(4.4 연동) + 서류스캔은 정적 "준비 중" 카드(OCR 파이프라인 없음, 순신규 분류) |
| ✅ 4.5c | PC 메시지 데스크톱 분기(4c) | 부분 확장 완료 | `MessagesPage`에 `useIsDesktop` 분기 추가 → `MessagesWorkbench`(스레드 목록·대화·연결 케이스 3열). M6 해석확인 로직은 ThreadPage(모바일)와 별도 구현(CaseWorkbench/CaseReviewPage 관계와 동일 원칙 — 공유 데이터층, 플랫폼별 프레젠테이션). |
| ✅ 4.5d | PC 발송 실행 큐(4d) | 순신규 완료 | `/cases/dispatch`(담당자 전용) — 각본 기반 고정 큐(`mocks/dispatch.ts`, 실제 승인 파이프라인 자동 연동은 후속), 실행 시 evidence(`dispatch_executed`) 기록 + 큐에서 제거. 신규 EvidenceType 2종(`dispatch_executed`/`delivery_confirmed`) — `types.ts`+`lib/audit.ts` 두 Record·`audit.test.ts` ALL_TYPES 갱신 완료. |
| ✅ 4.5e | 행정사 패키지 구조화된 회신(4e 확장) | 확장 완료 | `ExpertLinkPage`에 회신 폼(보완요청/검토완료/질문 + 자주 쓰는 요청 + 상세내용 + 기한) 추가 — 신규 EvidenceType `package_reply`. "담당자 케이스에 할일로 등록"은 M8 전역 판단 기록 수준까지만(케이스 타임라인 자체에 실시간 반영은 후속). 브라우저 실검증으로 테스트 파일의 `vi.resetModules()` 모듈 인스턴스 불일치 버그 발견·수정. |
| ✅ 4.5f | 사장님 PC 최소화면(4f) | 부분 확장 완료 | `HomePage`가 `role==='owner' && isDesktop`이면 `ControlTowerPage` 대신 `OwnerHomeWorkbench`(월간 리포트 정적 목데이터 + "승인은 모바일에서" 배너 + 구성원·위임 — companyStore 재사용) 렌더. |

**PC 나비 IA 결정**: 목업은 최상위 탭 7개(컨트롤타워/케이스/근로자/메시지/발송실행/거버넌스/설정)를
가정하지만 실제 Shell은 5개뿐(`Shell.tsx:11-17`) — 근로자·발송실행은 새 최상위 탭이 아니라
**케이스 하위 화면**으로 구현한다(컨트롤타워/거버넌스가 이미 브리핑/기록 데스크톱 분기로 들어가
있는 것과 동일 패턴). 이 IA 재정렬 자체는 계속 미결로 남긴다(2.5.6 HANDOFF에서부터 미결 기록).

**✅ M4.5 전 항목(4.1·4.4·4.5a~4.5f) 완료(2026-07-13).** 전체 스위트(352 테스트)·`tsc`·
`vite build` 클린, 각 화면 브라우저 실검증 완료. 이번 확장에서 의도적으로 다루지 않고
후속으로 남긴 것:
- 서류 스캔 자동분류(OCR 파이프라인) — 4b는 정적 "준비 중" 카드만.
- 발송 실행 큐(4d)의 승인 파이프라인 자동 연동 — 현재는 각본 기반 고정 큐, 승인 완료 시
  자동으로 큐에 항목이 추가되지 않는다.
- 행정사 구조화된 회신(4e)이 케이스 타임라인에 실시간 반영 — 현재는 M8 전역 판단 기록
  수준까지만(`CaseTimeline`이 `CASE_SHEETS` 정적 데이터만 읽는 구조라 별도 리팩터 필요).
- PC 나비 IA(52px vs 64px, 컨트롤타워/거버넌스 라벨) 재정렬 — 2.5.6부터 이어지는 기존 미결.

## M4.6 — 행정사 화이트라벨 (설계 + 동작 목업, 2026-07-14)

스펙 §7 "후속" 항목이었던 화이트라벨을 사용자 요청으로 선행 설계 + 목업까지 구현.
결정: 인증=영속 매직링크+개인 대시보드, 범위=여러 회사 통합 뷰 + 행정사 브랜딩, 산출물=설계
문서 + 동작 목업. 설계 문서: `reference/specs/7-1_행정사_화이트라벨_v0.md`.

| 항목 | 파일 | 비고 |
|---|---|---|
| 데이터 모델 | `types.ts`(Tenant/ExpertAccount/ExpertMembership) · `mocks/expert.ts` · `mocks/packages.ts`(tenantId + levan) | 스펙 §1 멀티테넌트 씨앗 실체화 |
| 개인 대시보드 | `features/expert/ExpertDashboardPage.tsx` (`/expert/:expertId`) | 여러 회사 검토 대기 통합, 브랜드 헤더 |
| 패키지 뷰 | `features/expert/ExpertPackagePage.tsx` (`/expert/:expertId/package/:packageId`) | DocumentPreview+회신 재사용, 소속 회사·뒤로가기, scope 검사 |
| 브랜드 헤더 | `features/expert/ExpertBrandHeader.tsx` | 행정사 로고/이름 + "외고반장 제공" |
| 회신 폼 추출 | `features/packagePkg/StructuredReplyForm.tsx` | ExpertLinkPage에서 분리, 두 화면 공유 |

**목업 vs 백엔드 경계**(문서 §3): 지금은 URL의 expertId=토큰(mock), 열람/회신 evidence는 실제
기록. 백엔드 필요 = 서명 토큰+이메일 OTP, tenant scope 서버 강제(404), 실 계정·초대 플로우.
`/link/:packageId`(단발 링크)는 유지 — 화이트라벨은 그 위 영속 계층이지 대체가 아니다.

## M4.7 — 행정사 화이트라벨 v1 (실사용 설계, 문서만 · 2026-07-16)

사용자 요청("설계를 추가로 하고 싶다")으로 M4.6(v0)을 실제 백엔드 구현 수준까지 심화한
후속 설계 문서. **코드 변경 없음** — v0의 목업(위 표)은 그대로 현재 구현이고, v1은 그
위에 얹을 백엔드/스키마/화면 확장 계획이다. 문서: `reference/specs/7-1_행정사_화이트라벨_v1.md`.

- legacy 백엔드(`legacy/backend/`) 실제 계약을 근거로 함: 인증 토큰 모델(서명 없는 demo
  token vs 미사용 상태의 JWT 디코더), tenant scope 해석기, PII allowlist(`_FORBIDDEN_KEYS`),
  Evidence Log 스키마의 "사람 열람 기록 없음" 공백.
- 신규 타입 설계: `ExpertGrant`(위탁 생애주기, status enum, 무기한 금지) · `ExpertOfficeMember`
  (사무소 내 개인 계정, PIPA 개인 단위 열람추적 요건) · `PackageViewLog`(열람 감사 로그,
  Evidence Log와 별도 테이블·보존정책).
- 3개 default 결정(문서 §9, 되돌리는 법 포함) — 사용자가 "끝까지 산출"을 지시해 차단하지
  않고 명시적 기본값으로 진행: **A** PII 노출 수준(이름·국적 평문 유지, 식별번호만 마스킹,
  `PiiFieldPolicy` 테이블로 뒤집기 가능) / **B** 계정 단위(사무소+개인 2층) / **C** 위탁
  근거(회사 단위 계약, 개별 근로자 동의 아님, 단 종료일 필수).
- **법무 미확정으로 명시적으로 남긴 것**(§5.5·§9·§10, "법무 검토 필요"): 위탁(§26) vs
  제3자 제공(§17) 법적 성격 분류가 결정 C 전체의 전제이며 아직 미확정, 정보주체
  처리정지요구권(§37)·열람권(§35) 경로 부재, §26②/④ 공개·정기감독 절차.
  **이 분류가 뒤집히면 `ExpertGrant`가 tenant 단위 → tenant+worker 단위로 스키마가
  커지는 큰 변경이 따른다** — 후속 mission 착수 전 최우선 확인 대상.
- 검증: Workflow(초안→4개 독립 렌즈 적대적 검증: 법률/기술/일관성/UX→최종본) 적용,
  §0.1에 초안→최종 반영 로그 전건 기록. 문서 자체 리뷰 완료, `tsc`/전체 스위트(360)/
  `vite build` 전부 클린(문서만 추가했으므로 회귀 없음, 재확인 완료).
- ~~GLOSSARY.md 불일치 발견(문서만, 아직 미수정): `Role` 유니온에 `expert` 없음~~ — R0.1에서
  재확인한 결과 `GLOSSARY.md:34`에 이미 `expert`가 반영돼 있어 불일치 없음(이 노트가 낡은 것이었음).

## M5 — RAG 인제스천 파이프라인 (legacy 자산 이식 · 백엔드 접속점 선행 작업)

> 근거: AGENTS.md §2(RAG=공식 근거와 절차를 찾는 곳), legacy/docs/RAG_STRATEGY.md(14필드 메타·evidence_grade·runtime boundary 정본 유지), legacy/docs/langchain-1-migration-plan.md(create_agent 패턴).
> 위치: 루트 `rag/` 독립 uv 프로젝트(Python 3.13 — backend/의 3.14 핀과 분리). VectorDB = **pgvector**(전용 `rag` PG 스키마, 정본 db/schema.sql 비침범, 로컬 컨테이너 `oegobanjang-rag-pg`:55433).
> legacy/는 읽기 전용 소스(복사·정제 이식) — legacy 수정이 필요해지면 그 시점에 별도 이관 mission을 연다. HWP/DOCX 파서는 범위 밖(수동 txt/pdf 변환 후 투입). src/ runEngine RunConfig 연동은 아래 "백엔드 접속점" 별도 계획 유지.

| # | 태스크 | 레벨 | DoD | 상태 |
|---|---|---|---|---|
| 5.1 | `rag/` 스캐폴드 + 코어 이식(raw_ingest·domain_splitters·metadata·chunking·embeddings) + 원천 데이터 복사 + 단위테스트 | L2 | `cd rag && uv run pytest` 전건 통과 (무손실·source_id 패리티 포함) | ✅ |
| 5.2 | VectorIndex 추상화 + PgVectorIndex + `rag ingest/index` CLI (멱등 upsert, provider 매니페스트) | L2 | deterministic 임베딩 index 2회 실행 멱등, count=입력 수 | ✅ |
| 5.3 | 런타임 retriever 이식 + `rag eval` 게이트 + CI `rag` 잡 | L2 | Hit@1≥0.60·Hit@3≥0.80·Hit@5≥0.90·MRR≥0.65·safety/misuse=0, CI 그린, `npm run verify` 비영향 | ✅ |
| 5.4 | LangChain 1.x `create_agent` + `@tool` retriever + `rag_retrieved` 이벤트 계약 | L3 | FakeChatModel 오프라인 스모크, D/F등급 차단, 이벤트에 민감정보 원문 없음 | ✅ |
| 5.5(후속) | Playwright 크롤러 `[crawl]` extra / OpenAI 운영 인덱스(≈$0.02) / langgraph-checkpoint-postgres / 백엔드 접속점 연동 | L2 | 각 태스크 DoD | ⬜ |
| 5.6 | 비자서류 검색(rag_hyunwook 이식) — workforce_official 재필터링 | L2 | `search_policy_documents` 테스트 통과, D/F 근거 구조적 노출 불가 확인 | ✅ |
| 5.7 | 다국어 컨택 RAG(rag_hyunhee 이식) — 별도 `multilingual_contact` 컬렉션 | L2 | HTML 정제 검증 테스트 통과, `search_multilingual_contact_materials` pgvector 통합 테스트 통과 | ✅ |

검수 노트(2026-07-17): legacy 커밋 산출물(all_chunks.jsonl 964청크, 2026-05)은 doc_type 청킹 도입 이전 것이라 텍스트 비교 기준으로 쓸 수 없었고, legacy 청킹 코드의 "첫 헤딩 이전 서두 유실" 버그를 이식 시 수정했다(`rag/src/oe_rag/chunking.py:_preamble_chunks`). 재생성 기준: 2033청크, workforce 컬렉션 945+38.

검수 노트(2026-07-17, M5.6/M5.7): Understand 워크플로 조사 결과 rag_hyunwook은 별도 raw 코퍼스가 없어(law/eps 원문을 workforce_official과 공유) 신규 컬렉션 대신 기존 컬렉션 재필터링으로 이식했고(legacy 설계 문서가 명시적으로 통합을 권고), legacy의 evidence_grade D/F 자동 차단 누락 가드레일 공백을 수정했다(색인 단계에서 이미 배제되므로 구조적으로 불가능). rag_hyunhee는 원본 raw HTML(life_guides/safety)이 `.gitignore`로 소실돼 사전 빌드 청크 JSONL(1022건)만 정본으로 이식했고, 로드 과정에서 원본의 47%가 HTML 태그 잔재로 오염돼 있던 버그를 발견해 정제 로직을 추가했다(정제 후 379건 채택, 643건 격리 — 순수 boilerplate/스크립트 잔재).

## M7 — 발표 아키텍처 오케스트레이션 (Router·Rule·3미션·Approval·Evidence)

> 근거: 발표 수정본 p.16 Agent Pattern(입력채널→Intent Router→Risk Rule Engine→Mission Agent→Approval Gate→Evidence, "Rule이 케이스를 확정하고 LLM은 승인 가능한 초안만") + 사용자 학습 노트 week3_5(명시적 StateGraph 결정) + `plans/BACKEND_CONNECT.md` 토폴로지.
> 실행 모델 = 하이브리드: 바깥 고정 파이프라인은 명시적 LangGraph StateGraph, 미션 내부는 LangChain 1.0 요소(with_structured_output·@tool·middleware). 상태 소스 = backend가 rule 결과 포함 ContextSnapshot을 주입(2-phase: /intent → /graph/run). B1 create_agent(/agent/run)는 무수정 공존.
> legacy는 읽기 전용 소스(함수 발췌 이식 — middleware.py 데드코드·visa_agent 자유루프는 구조 변경 이식).

| # | 태스크 | 레벨 | DoD | 상태 |
|---|---|---|---|---|
| G1 | 계약·가드 계층 이식 — `orchestration/{contracts,guard,router,planner}.py` (Intent 8종·5등급·EventType 9종·승인액션 레지스트리·PII/금지어·12-intent 키워드 라우터·미션 매핑 dict) | L2 | 키 없이 `cd rag && uv run pytest` 그린, 기존 테스트 무회귀 | ✅ |
| G2 | Risk Rule Engine + ContextSnapshot (backend) — `domain/rules.py`(순수 5함수+임계표) + `services/context_service.py` | L2 | backend pytest 그린, seed 기대값(D-20→HIGH 등), 스냅샷 PII 원문 부재 | ✅ |
| G3 | StateGraph 골격 + `/intent`·`/graph/run` SSE — input_guard→router→planner→executor(순차)→aggregator→approval_gate→evidence | L3 | 키 없이 SSE 스텝 순서·차단 경로 테스트, curl 스모크 | ✅ |
| G4 | M2 비자·서류 미션(rule 소비+LLM 1회+오프라인 폴백) | L3 | 오프라인 E2E + LLM이 severity 못 바꾸는 가드 테스트 | ✅ |
| B3' | backend 오케스트레이터+runs SSE(2-phase 중계, RunStep 기록, 승인 생성) | L3 | fake rag 통합 테스트, seed 1런에 runs·evidence·approvals 행 생성 | ✅ |
| G5 | M1 인력확보(채용준비·후보자준비) + M3 다국어컨택(온보딩·답변해석) | L3 | 미션별 오프라인 E2E, approval_required 고정, PII 미노출 | ✅ |
| G6 | 데일리 브리핑(backend rule-only·LLM 0회) `POST /api/v1/briefings/generate` | L2 | seed 브리핑 스냅샷 테스트, risk_flagged evidence | ✅ |

> `backend/`·`rag/` 서비스 자체의 상세 계획: `plans/BACKEND_CONNECT.md` (M6 — B1 rag 서비스화 ✅ → B2 backend RAG 클라이언트·근거 영속화 ✅ → B3 runs SSE(M7 B3'로 개정) ✅ → B4~B6은 아래 R2가 실제로 흡수해 진행). 프론트(`src/`)를 이 backend에 배선하는 작업은 아래 R2가 정본이다 — M7 완료 시점에 작성했던 "백엔드 접속점 (이후 — 별도 계획)" 절은 R2가 실제로 그 배선을 시작·상당 부분 완료해 R2로 대체됐다.

## R0 — 부채 청산 · 문서 정합화 (2026-07-17, `plans/NEXT_ROADMAP_2026-07-16.md` §2 R0 승격)

전체 코드 검수(2026-07-16, `plans/NEXT_ROADMAP_2026-07-16.md`)에서 발견된 문서 불일치·버그·구조적
부채를 해소하는 선행 단계. R1(목 세계 플로우 완결)~R5(파일럿 확장) 착수 전 필요 — 특히 R2(백엔드
배선) 전에 0.3(메시지 도메인 단일화)을 끝내야 API 계약을 두 벌 만들지 않는다(NEXT_ROADMAP §2 서두).

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 0.1 | 문서 일괄 정합화 | L1 | NEXT_ROADMAP §1.5 DOC-1~8 | "루트 backend 없음" 서술을 실제 `backend/`(OTP 인증·승인 요청 생성 포함)에 맞게 갱신, 수치 정합(33테이블/178검증), 로스터·경로 오기 수정, `DESIGN.md` 이관 |
| ✅ 0.2 | 버그 수정 | L1 | NEXT_ROADMAP §1.4 B-1~4 | 동일 사유 재반려 유실 회귀 테스트 통과, 스레드 픽스처 dangling 참조 정리 + threadIdForCase 매핑 보강, CSV 템플릿 다운로드 버튼 동작 |
| ✅ 0.3 | 메시지 도메인 단일화 | L2 | NEXT_ROADMAP §1.3 D-1 | `MessagesWorkbench`가 `threadStore` 기반으로 전환, `mocks/messages.ts` 제거, 모바일·PC 동일 스레드 표시, 기존 테스트 전건 통과 |
| ✅ 0.4 | Badge→Chip 마무리 | L1 | NEXT_ROADMAP §1.3 D-2 | `ThreadListItem`·`InterpretationCard`가 Chip 사용, `Badge`/`badgeTone.ts` 삭제 |
| ✅ 0.5 | 케이스 타임라인 스토어 승격 | L2 | NEXT_ROADMAP §1.3 D-3 | 행정사 회신(`package_reply`)·해석 확인(`interpretation_confirmed`)이 케이스 타임라인에 실시간 반영되는 테스트 통과 |
| ✅ 0.6 | 파생 로직 통합 | L1 | NEXT_ROADMAP §1.3 D-4·D-5 | 정렬·docUpdates 오버레이·EVIDENCE_SEED 병합·SEVERITY_LABEL 중복 제거, selector 단일화, 기존 테스트 전건 통과. **D-5(Page/Screen/Workbench 명명)는 NEXT_ROADMAP이 명시한 대로 "리네임 비용 대비 효과" 판단상 이번엔 미적용** — 라우트·테스트·스냅샷 전반에 걸친 리네임 비용이 순수 네이밍 일관성 이득보다 커서 보류 |

**R0 완료(2026-07-17).** `npm run verify`(typecheck→lint→test 424건→build) 전부 PASS, 브라우저
실검증(메시지 워크벤치 해석 확인→케이스 타임라인 실시간 반영→CSV 템플릿 다운로드) 완료.

## R1 — 목 세계 안에서 플로우 완결 (2026-07-17, `plans/NEXT_ROADMAP_2026-07-16.md` §2 R1 승격)

R0 완료 직후 한때 "R1을 건너뛰고 R2로 바로 진행"하기로 했었으나, 별도 세션(PR #16)이 이
지시를 모른 채 R1.1~1.8을 이미 구현했다. PR #16 리뷰(병합 보류 권고 — 이전 리뷰 수정 미반영
재발 3건 + 신규 P1 1건, `plans/HANDOFF.md` 참조)를 거친 뒤, 사용자가 R1을 재구성 범위에
포함하기로 확정해 이 세션에서 main(R0+R2.1+R2.2 반영 상태) 위에 R1 커밋을 다시 얹었다.
백엔드 없이 가능한 제품 완성도 — 지금까지 입력을 받고도 버리던 지점(회사 프로필·온보딩
근로자·CSV·커맨드 바·초안 수정·사장님 리포트)을 실제 상태로 이어 붙인다.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 1.1 | 회사 프로필 슬롯 | L1 | NEXT_ROADMAP 1.1, M-8 | `companyStore.profile` 추가, 온보딩 O3 입력이 완료 시 반영되어 홈(`BriefingHomePage`)·케이스 목록(`CaseListPage`) 헤더의 회사명이 그 값을 따르는 테스트 통과 |
| ✅ 1.2 | 온보딩 근로자 → 실제 케이스 생성 | L1 | NEXT_ROADMAP 1.2, M-8 | O4 입력값이 `lib/csvUpload.workerToCard`(CSV와 동일 데이터 계약, `onboard-` 접두)로 실제 `CaseCard`가 되어 caseStore에 반영되는 테스트 통과. 데모 6인 로스터는 그대로 유지(비파괴) |
| ✅ 1.3 | 케이스 타임라인 런타임 이벤트 반영 | L1 | NEXT_ROADMAP 1.3, D-3 | R0.5가 이미 충족 — 신규 코드 없음(검증만) |
| ✅ 1.4 | 승인 완료 → 발송 큐 자동 연동 | L2 | NEXT_ROADMAP 1.4, M-2 | 고정 `DISPATCH_QUEUE` → `lib/dispatch.deriveDispatchQueue`(approvalStore+evidenceStore 파생)로 교체, actionId를 실제 승인 파이프라인과 통일, "승인된 것만 도착" 구조적 보장 테스트 통과 |
| ✅ 1.5 | CSV 실제 파일 파싱 | L1 | NEXT_ROADMAP 1.5, M-5 | `lib/csvUpload.parseCsvText` 신설(파싱 즉시 `maskId()` 마스킹) + `CsvUploadWorkbench`가 실제 파일 선택·드래그앤드롭을 처리 |
| ✅ 1.6 | 커맨드 바 최소 매핑 | L1 | NEXT_ROADMAP 1.6, M-7 | `lib/commandBar.resolveCommandRunKey` 신설(워커명 키워드 → 실제 승인 런, 미매칭 시 폴백) + 추천 칩 클릭 시 즉시 제출 |
| ✅ 1.7 | 초안 수정 요청 개선 | L1 | NEXT_ROADMAP 1.7, M-9 | `DraftPage` 수정 요청 시트가 편집 가능한 textarea(제안값으로 미리 채움)로 전환 |
| ✅ 1.8 | 사장님 리포트 파생화 | L1 | NEXT_ROADMAP 1.8, M-10 | `lib/ownerReport.deriveMonthlyReport` 신설(처리한 케이스·사전 감지·승인 없는 발송 파생) — 평균 승인 소요만 D-6(실벽시계·데모 날짜 혼용) 사유로 mock 유지 |

**R1 완료(2026-07-17, PR #16 재구성).** 상세 verify 결과는 R2(2.1~2.3) 완료 기록과 함께 아래에
남긴다(같은 세션에서 R1+R2.3을 이어서 재구성했다).

## R2 — 백엔드 배선 (mock → `backend/` + 영속성) ★ 가장 큰 전환점

> 전제: `backend/`에 인증(OTP/세션)·승인 결정 API는 이미 있었다(R0.1에서 확인). 없던 것은
> ①프론트의 호출 코드, ②케이스/브리핑/스레드 read API, ③위임 유효성 검증 — 순서대로 배선한다.
> 원칙: mock/실서버 전환은 `src/lib/api/config.ts`의 `API_MODE` 플래그 하나로만 가른다(기본값
> `mock` — 기존 424개+ 프론트 테스트·8단계 데모 대본이 전부 mock 세계관을 전제하므로, `real`은
> `.env.local`의 `VITE_API_MODE=real` 명시적 opt-in일 때만 켜진다). 승인은 "서버 확정 후 반영"
> (GOTCHAS §2) 원칙을 배선 후에도 유지한다.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 2.1 | API 클라이언트 계층 | L2 | NEXT_ROADMAP R2.1 | `src/lib/api/`(config·client·auth) 신설, mock 기본값 유지, `apiFetch` 성공/실패/204 테스트 |
| ✅ 2.2 | 인증 배선 | L2 | NEXT_ROADMAP R2.2, M-4·M-6 | 온보딩 O1이 real 모드에서 `POST /api/v1/auth/otp/*` 실호출, `sessionStore` 세션 영속화(localStorage, 부팅 시 복원), `roleStore`가 세션 멤버십에서 파생(새로고침 시 manager 복귀 문제 해소) — 백엔드 `GET /api/v1/auth/me` 신설 포함 |
| ✅ 2.3 | 읽기 API 신설+배선 | **L3(2~3세션)** | NEXT_ROADMAP R2.3, M-6 | backend에 케이스/브리핑/스레드 read endpoint 신규 구현(`GET /api/v1/cases`·`/briefings/latest`·`/threads`·`/threads/{id}`, `get_current_membership`으로 company 스코프) + 프론트 `lib/api/{cases,briefings,threads}.ts` 어댑터·`lib/dataSeed.ts`(`useSeedCases`/`useSeedThreads`/`useSeedThreadDetail`) 신설, 13개 화면 배선. 여기서 M-6 영속성이 해소된다 |
| ✅ 2.4 | 승인 결정 배선 | L2 | NEXT_ROADMAP R2.4, M-4 | ApprovePage → `POST /api/v1/approvals/{id}/approve\|reject`(real 모드). PIN 서버 측 검증 승격(users.pin_hash 대조) + checklist 제출 반영, 위임(delegation) 유효성 검증 구현(트리거 OR-arm + 서비스 검증, `docs/DB_SCHEMA.md` §13-10 해소) — 신규 `GET /api/v1/cases/{id}`(체크리스트·근거수·guardNote·pending approval id)·`GET /api/v1/delegations/mine`. 반려도 PIN 게이트 통일(사용자 결정, DB 정본과 UX 일치) |
| ✅ 2.5 | Evidence 서버 영속화 | L2 | NEXT_ROADMAP R2.5 | `POST/GET /api/v1/evidence` 신규(인증 필요, PII 패턴 차단, 테넌트 격리) + 프론트 `lib/api/evidence.ts`·`evidenceStore.append`가 real 모드에서 자동 서버 기록·`useSeedEvidence` 부팅 시 hydrate. 민감정보 원문 미저장 원칙 유지(요약만, 해시만) |
| ✅ 2.6 | 행정사 링크 서버 강제 | L2 | NEXT_ROADMAP R2.6, M-11 | `POST /api/v1/packages/{case_id}/link`(발급/재발급, manager·owner 인증 + 케이스의 `create_handoff` 승인 완료 필요) · `GET /api/v1/packages/link/{link_token}`(열람, 무인증) 신규 — `/link/:linkToken`이 real 모드에서 서버 만료 판정을 따른다(클라이언트 `isLinkExpired()` → 404 강제, 만료·미발급·대상없음 모두 동일 404로 존재 비노출). `link_token`은 발급/재발급마다 회전(코드리뷰 지적 — `case_id`는 불변이라 비밀로 못 씀). 패키지 문서 콘텐츠 자체는 여전히 프론트 mock(범위 밖, 문서화된 경계) |

**2.1+2.2 완료(2026-07-17).** 실제 로컬 PostgreSQL(`oegobanjang-pg` 컨테이너, 시드 데이터 포함)에
`alembic stamp head`로 정합 후 backend pytest 110건 전부 PASS. 브라우저 실검증: 실 uvicorn +
프론트(`VITE_API_MODE=real`)로 시드 계정(010-0000-0001·담당자)의 OTP 로그인 전체 흐름
(request→verify→me) 성공, roleStore가 실제 멤버십(manager)으로 정확히 파생, 새로고침 후 세션이
`GET /me` 재호출로 복원됨(하드코딩 기본값 아님)을 네트워크 로그로 직접 확인.
**버그 발견·수정**: 이 저장소의 vitest 실행 경로에서 Vite의 "`--mode test`에서는 `.env.local`
제외" 문서화된 예외가 실제로는 적용되지 않아, 로컬 실서버 검증용 `.env.local`이 테스트
스위트에 새어 들어가 mock 모드 테스트가 깨지는 것을 발견 — `API_MODE` 계산에
`import.meta.env.MODE !== 'test'` 가드를 추가해 테스트는 로컬 dotfile과 무관하게 항상 mock이
되도록 교정(`src/lib/api/config.ts`). 2.4~2.6은 후속 세션에서 순차 진행한다.

**2.3 완료(2026-07-17, PR #16 재구성 세션).** 케이스/브리핑/스레드 읽기 엔드포인트 신규 구현 +
프론트 배선. 이 세션에서 R1(위 절)도 함께 재구성했다 — 자세한 경위(PR #16 리뷰에서 병합 보류
권고 → 재구성 결정, PR #15가 실제로는 main이 아니라 다른 브랜치에 병합됐던 사실 발견 등)는
`plans/HANDOFF.md` 최상단 항목 참조. **코드리뷰 지적 수정**: real API 스레드 목록이
`interpretationStatus`를 항상 `'none'`으로 반환해 응답 도착 배지·정렬이 죽어 있던 버그를
백엔드(`ThreadOut.latest_interpretation_status` 신설 + 배치 쿼리)·프론트(`toThreadSummary`)
양쪽에서 수정. `npm run verify`(typecheck→lint→test 515건→build) 전부 PASS, backend
`uv run pytest` 128건 전부 PASS.

**2.5+2.6 완료(2026-07-17).** 사용자 지시로 2.4(승인 결정 배선)를 건너뛰고 2.5·2.6을 먼저
진행했다 — ApprovePage의 실제 승인/반려는 여전히 mock(2.4가 후속 세션 몫)이지만, 감사 기록
서버 영속화와 행정사 링크 서버 강제는 그와 독립적으로 완결 가능한 범위였다. 상세 경위·설계
판단은 `plans/HANDOFF.md` 최상단 항목 참조 — 요약:
- `db/schema.sql`의 `evidence_events.type` CHECK가 프론트(`src/types.ts EvidenceType`)보다
  뒤처져 있던 것을 발견(7종 누락 — `approval_rejected`·`interpretation_confirmed`·
  `package_link_issued/viewed`·`dispatch_executed`·`delivery_confirmed`·`package_reply`)해
  함께 정합화했다.
- `backend/migrations/versions/0001_...`은 실배포 시점(PR #10) 동결 스냅샷이라 더 이상 손대지
  않는다 — 이번 스키마 변경은 `0002_r2_5_evidence_and_r2_6_package_links.py`(ALTER 리비전,
  down_revision=0001)로 표현했다. 이후 스키마를 또 바꿀 땐 0002도 아니라 0003+을 새로 만든다.
- `handoff_packages.link_issued_at/link_expires_at` 2컬럼을 신설해 링크 발급/재발급/만료를
  서버가 직접 보유한다(별도 `package_links` 테이블은 만들지 않음 — 패키지당 링크 1개 모델).
- 승인 결정(2.4)이 아직 실서버에 안 붙어 있어 `action_id`/`approval_id`/`run_id`가 real 모드에서도
  mock 세계관의 값이라 실제 DB 행을 보장 못 한다(트리거 `trg_evidence_context_match`가 이걸
  검증한다) — `POST /api/v1/evidence`는 그래서 이 세 필드를 아예 받지 않는다(`case_id`만,
  R2.3부터 real 모드 caseId는 항상 진짜라 안전). 2.4가 배선되면 재검토 대상.
- `package_link_viewed`/`package_link_issued`/`package_reply`는 일반 evidence 엔드포인트가
  거부한다(422) — 무인증 화면(ExpertLinkPage)이 호출할 수 없는 인증 필요 엔드포인트라서다.
  전용 `POST /api/v1/packages/{case_id}/link`·`GET /api/v1/packages/link/{link_token}`가
  자기 트랜잭션 안에서 직접 기록한다.
- **주의(다음 세션이 알아야 할 것)**: 이 워크트리가 쓰는 로컬 dev Postgres 컨테이너
  (`oegobanjang-pg:55432`)의 `alembic_version`이 이미 `'0002'`로 찍혀 있었다 — 이 저장소
  git 이력에는 없는(커밋된 적 없는) 이전 세션의 미완료 R2.4 마이그레이션 시도 흔적으로
  보인다(`__pycache__`에만 `0002_r2_4_delegated_approval_decider.cpython-*.pyc` 잔존).
  이번 세션은 그 컨테이너를 건드리지 않았다(backend pytest는 세션마다 새로 만드는 격리
  `ogb_test` DB만 쓴다) — 하지만 그 컨테이너에 `alembic upgrade head`를 그대로 돌리면
  revision id가 우연히 `'0002'` 문자열로 겹쳐 이 커밋의 실제 ALTER가 적용 안 된 채
  "이미 최신"으로 오판될 위험이 있다. 다음에 그 컨테이너로 실서버 브라우저 검증을 하려면
  먼저 `alembic_version` 실제 내용과 스키마 상태(예: `evidence_events` CHECK 제약, `handoff_packages`
  컬럼)를 대조 확인할 것.

**2.5+2.6 코드리뷰 2라운드 수정(2026-07-17~18).** PR #20 리뷰에서 병합 보류 권고 받은 P1 총 7건 +
P2 1건을 모두 수정했다(상세는 `plans/HANDOFF.md` 참조). 1라운드(P1 4건): 링크 발급 시 케이스
승인 상태를 전혀 확인하지 않던 것(AGENTS.md §8 위반) → `create_handoff` 승인 완료 전제조건
추가, `case_id`(불변)를 공개 링크 비밀값으로 쓰던 것 → 발급/재발급마다 회전하는 `link_token`
도입, 일반 evidence 엔드포인트가 `approval_decided`/`role_changed` 등 특권 이벤트까지 받아
위조 가능하던 것 → `PRIVILEGED_EVIDENCE_TYPES` 거부 목록 추가, real 모드 mock/real id 불일치
(`batbayar` vs `cs_batbayar`) → 라우트 파라미터·`REAL_CASE_ID_ALIASES`로 정합. 2라운드(P1 3건 +
P2 1건): 재발급 API 실패에도 UI가 성공으로 기록하고 응답의 `link_token`을 쓰지 않던 것 →
성공 시에만 evidence 기록 + 공유 URL 노출, evidence의 `summary` 외 자유 텍스트 필드
(`input_hash`/`output_hash`/`trace_id`/`request_id`/`payload_ref`)로 PII 우회 저장 가능하던
것 → 전 필드 검사, real 모드 행정사 구조화된 회신이 서버 저장 없이 "보냈습니다" 표시하던 것
(백엔드 미구현) → real 모드에서는 성공 표시 대신 정직한 "준비 중" 안내, 문서(`backend/README.md`·
`docs/DB_SCHEMA.md`)의 GET 경로 표기가 구 `case_id` 경로로 남아있던 것 → `link_token` 경로로 갱신.

**2.4 완료(2026-07-18).** R2 마일스톤 전체 완결. 상세 경위·설계 판단은 `plans/HANDOFF.md`
최상단 항목 참조 — 요약:
- 착수 전 발견한 두 구조적 공백을 함께 해소했다: (A) real 모드 ApprovePage가 참조하던
  체크리스트·근거수·가드노트가 전부 mock `CASE_SHEETS`(슬러그 키)에 묶여 있어 real caseId와
  매칭되지 않았고, (B) 승인/반려 엔드포인트가 `approval_id`로 식별되는데 프론트가 이를 얻을
  방법이 없었다 — 신규 `GET /api/v1/cases/{case_id}`(usable_citation_count·guard_note·
  pending_approval{id,checklist})로 둘 다 해소했다.
- `trg_approvals_decider_role` 트리거에 위임 OR-arm을 추가 + 서비스 계층 `_validate_delegation`
  선검증 — `backend/migrations/versions/0003_r2_4_delegated_approval_decider.py`(0002는 R2.5/2.6이
  점유, ALTER 리비전). 위임 있는 대리 결정 시 **기존 manager 정책 게이트(owner_only+LOW 근사)를
  건너뛰어야 한다**는 것을 테스트로 잡아 교정(안 그러면 위임이 있어도 owner_only+비LOW
  케이스에서 여전히 403).
- PIN을 `users.pin_hash` 서버 대조로 승격(`hash_secret`/`secrets_match` 재사용, OTP·세션
  토큰과 동일 HMAC-SHA256+pepper 원리) — 시드 3인의 `pin_hash`를 데모 PIN '1234'로 채움
  (`.env`로 pepper를 바꾸면 깨짐, 시드 주석에 재생성 커맨드 명시).
- **사용자 결정 2건**: (1) 반려도 PIN 본인확인 통일(DB 정본이 승인·반려 모두 요구) — mock
  모드 반려 플로우에도 PIN 시트를 추가, 기존 `approvalFlow.test.tsx`의 반려 테스트 5건에
  PIN 스텝을 넣어 개정. (2) 진입 퍼널은 ApprovePage(2c) 완전 전환 + CaseReviewPage(2b) 최소
  폴백(카드+guardNote만, 풍부한 mock 콘텐츠 재현은 범위 밖) — 2b도 real caseId에서 mock 시트가
  없어 "케이스를 찾을 수 없습니다"가 뜨던 문제를 해소.
- `useApprovalActions.approve/reject`를 `Promise<boolean>`으로 전환하되 **mock 분기는 기존
  동기 변이를 그대로 유지**(신규 테스트로 확인) — real 분기만 서버 확인 후 로컬
  approvalStore/caseStore를 미러링한다(GOTCHAS §2, 낙관적 갱신 금지). 결정 evidence
  (`approval_decided`/`approval_rejected`)는 서버가 자기 트랜잭션에서 이미 기록하므로 로컬
  재기록하지 않고 `fetchEvidence()+hydrate`로 재동기화한다.
- reject의 evidence type이 approve와 동일하게 `approval_decided`로 오기록되던 버그를 발견·수정
  (`approval_rejected`로 교정 — R2.5에서 CHECK엔 이미 있었으나 서비스가 안 썼다).
- `db/validate.py` 178→181건(위임 대리 결정 성공/만료/철회 3건 추가, 기존 `cs_other` 케이스를
  재사용하면 뒤쪽 전이 검증이 오염돼 전용 `cs_other_delegated` 케이스로 분리).
- **검증 중 발견한 인프라 이슈(코드 버그 아님)**: 이 워크트리와 같은 Postgres 컨테이너를 쓰는
  형제 워크트리 세션이 backend pytest의 기본 테스트 DB 이름(`ogb_test`)에 동시 접근해
  일시적으로 스키마 충돌(`handoff_packages.link_token`이라는, 이 브랜치에 없는 컬럼이 관측됨)이
  발생했다 — `TEST_DB_NAME` 환경변수로 격리된 이름을 쓰면 재현되지 않음을 확인, 실제 원인이
  아님을 확인했다. 여러 세션이 동시에 backend pytest를 돌릴 때는 `TEST_DB_NAME`을 각자 다르게
  지정할 것.
- 검증: backend `uv run pytest` 171/171(격리 DB), `db/validate.py` 181/181, 프론트
  `npm run verify`(typecheck→lint→test 561건→build) 전부 PASS.

## 발송 어댑터·알림톡 (R2 이후 — 별도 계획, PRD Sprint 6)

발송 어댑터·알림톡은 R2 배선과 별개로 계속 범위 밖이다¹.

¹ outbox(발송 대기열)+`SmsAdapter`+응답 링크 인바운드까지의 로드맵은 `docs/MESSAGING_CHANNELS.md` §5(단계 로드맵)에 정리돼 있다 — 이 저장소는 현재 ①(프론트 Message 도메인 + `MockAdapter`)까지만.

## R5.4 — 알림 생성·큐잉 + 인앱 알림 센터 (푸시 발송은 자격증명 게이트 스텁, 2026-07-20)

> 출처: `plans/NEXT_ROADMAP_2026-07-16.md` §5.4 "알림·푸시 — 알림 카탈로그(N01~) 실발송 — 딥링크
> 맵은 이미 구현돼 있어 수신부만"의 승격. `notifications` ORM 모델은 이 태스크 착수 전까지
> 어떤 서비스·라우터에서도 쓰이지 않았다(P3 미구현 10테이블 중 하나). §13-7 "MVP는 발신 확인
> 없음" 설계(`notifications.status`는 `queued/held/suppressed`만, `sent`/`delivered`/`failed`는
> DB CHECK가 구조적으로 차단)는 그대로 유지 — 이 태스크는 알림 큐 **생성/조회**와 인앱 알림
> **센터**만 실구현하고, 외부 푸시 발송 자체는 자격증명 게이트 뒤 로그 전용 스텁만 둔다.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 5.4 | 알림 생성/큐잉 + 인앱 센터 | L2 | NEXT_ROADMAP §5.4, 2단계_알림카탈로그_딥링크맵_v1.md | `backend/app/services/notifications.py` 신설 — 서버가 이미 감지하는 이벤트 3종(승인 요청 N01·승인/반려 결정 N06·CRITICAL 리스크 N03)에 배선(`services/approvals.py`·`services/briefing_service.py`). `GET/POST /api/v1/notifications`(목록·읽음 처리, 본인 수신함 스코프) + `notifications.read_at` 컬럼 신설(마이그레이션 `0006_r5_4_notification_read_at.py`, `sent_at`/`delivered_at`과 무관 — §13-7 유지). 프론트 `src/lib/api/notifications.ts`(citations.ts/briefings.ts 관례)·`src/stores/notificationStore.ts`·`src/features/notifications/NotificationBell.tsx`(bell+BottomSheet, Shell.tsx nav 신규 진입점)·`src/features/briefing/BriefingHomePage.tsx`의 `unreadNotifications:0` 하드코딩을 real 모드 실카운트로 교체(mock 모드는 무변경). 푸시 발송은 `backend/app/services/push_adapter.py`(자격증명 게이트 스텁, `PUSH_PROVIDER_CREDENTIALS` 미설정 시 로그 전용 no-op — 이 저장소·CI·리뷰어 환경 전부 해당) |

**5.4 완료(2026-07-20).** 서버가 이미 감지하는 이벤트에만 배선했다 — N02(worker_replied)는
인바운드 쓰기 API 자체가 없어(A3, R3 몫) 소스가 없고, N04/N05(런 상태 전이)·N10~N14(아침
다이제스트 스케줄러)·N20~N22(주간 묶음)는 스코프 밖(후속)이다. 발견·교정한 실제 버그: 여러
수신자(owner+manager)에게 같은 이벤트를 알릴 때 `dedupe_key`에 수신자 id를 넣지 않아
`UNIQUE(company_id, dedupe_key)` 충돌로 두 번째 수신자부터 알림이 조용히 유실되던 것을
`test_notifications_service.py`가 잡아 교정(`{case_id}:{type}:{...}:{recipient_id}`로 변경).
검증: backend `TEST_DB_NAME=ogb_test_r54 uv run pytest` 258/258(신규 18건 포함) 전부 PASS,
`db/validate.py --reset`(디스포저블 DB `ogb_r54_validate`) 181/181 PASS("notification sent
status is blocked" 등 §13-7 가드레일 불변, `read_at` 추가와 무충돌 확인). 프론트
`npm run verify`는 하단 기록 참조.
