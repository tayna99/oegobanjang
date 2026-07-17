# ROADMAP — 마일스톤 · 태스크 스펙 · DoD

> 태스크 1개 = Claude Code 세션 1개 크기. 순서대로. 각 태스크: 위임 레벨(L1 자율 / L2 계획 승인 / L3 협업) + 읽을 스펙 + DoD(검증 명령).
> 진행 기록은 `plans/HANDOFF.md`에 남긴다 (에이전트가 태스크 종료 시 갱신).
> 디자인 기준(2026-07-11 확정): claude.ai/design "Mobile screen design" 프로젝트의 **Montage(Wanted) 시스템** — `rules/design.md`(v2)와 `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` 참조. 전환 작업은 M2.5.

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
| ✅ 2.2 | 메시지 탭 + 스레드 대화 뷰 + M6 응답 해석(isFinal:false→확인) — 목록 원문 미노출, 원문은 스레드 내부만. main 병합(2026-07-16) 후 정본은 `threadStore`/`mocks/threads.ts` 기반 구현(`features/messages/MessagesScreen.tsx`, `features/thread/*`) — PC 4c(`MessagesWorkbench`)는 별도 mock(`mocks/messages.ts`)을 쓰는 독립 데스크톱 화면으로 그 위에 병존 | L2 | 1단계 M6, 탭별기획 §3, 블루프린트 §9-A | 해석 확인 시 상태 갱신+evidence 테스트 |
| ✅ 2.3 | M8 판단 기록 (타임라인·필터·이벤트 상세 시트·딥링크 하이라이트) — 모바일 /evidence, audit.ts 재사용 | L1 | 1단계 M8, 탭별기획 §4 | 해시만 표시(원문 없음) 테스트 |
| ✅ 2.4 | 행정사 패키지 화면 — 대상 케이스 Batbayar(블루프린트 §3 로스터), 포함 항목 토글·검토 요청서·PII 마스킹·승인 게이트 내보내기+이력 | L1 | PC.dc.html 운영관제형 §2d, 블루프린트 §1 | 승인 흐름 단계 렌더 테스트, 내보내기 승인 게이트 테스트 |

## M2.5 — 디자인 시스템 v2(Montage) 전환 · PC 확장 화면

> 근거: `reference/design-system/외고반장 PC.dc.html`(저장소에 고정된 사본, 원본은 claude.ai/design `bd0fd8f8-615f-48e9-875b-eb5c9e9b398d` — 고정 경위는 `reference/design-system/README.md`)의 **통합 재설계(3a·3b·3c) — 사용자 확정(2026-07-11)** + `rules/design.md`(v2) + `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`(매핑표 §3, 판단 §5).
> 순서: 2.2~2.4 착수 전에 2.5.1~2.5.3을 먼저 끝내는 것을 권장(신규 탭을 v2 토큰으로 바로 구현해 이중 리스킨 방지). 2.5.6은 M3 완료 후.
> 결정(2026-07-11): CSV 업로드 화면 → **4.4로 신설**(아래 M4 표). 모바일 개편안(`reference/design-system/외고반장 Mobile.dc.html` 승인 큐 중심) → **보류, M2.5 범위 밖**(사유: AUDIT §5-4).

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.5.1 | tokens.css v2 — Montage atomic+semantic 2계층·light/dark(`[data-theme="dark"]`) 이식, Tailwind theme `var(--color-*)` 재배선, PC 밀도 타입램프(10.5~13.5px) 토큰 등록 | L1 | rules/design.md(v2) §1·2·3, colors_and_type.css | 토큰 스냅샷 갱신, 다크 테마 스위치 렌더 테스트, Pretendard 로드 확인, PC 타입램프 임의값 0건 |
| 2.5.2 | 공용 컴포넌트 v2 — Badge→Chip 개명·severity 색표 교체, Button/Card 라디우스·아웃라인(inset box-shadow)·모션(0.2s ease) 전환 | L2 | rules/design.md(v2) §4·5 | Chip severity 색 규칙 테이블 테스트, 아웃라인 inset box-shadow 스냅샷, 기존 테스트 전건 통과 |
| 2.5.3 | 기구현 화면(M1 전체·2.1 케이스 목록) v2 리스킨 + ui-matcher 기준을 디자인 프로젝트로 교체 + rules/design.md 부록 A 삭제 | L2 | AUDIT §3 매핑표 | 1.6 E2E 통과, verify PASS, 임의 hex 0건(verifier grep) |
| 2.5.4 | PC 케이스 워크벤치(3b, 3열: 목록·상세·AI 패널) — Shell lg+ 레이아웃 확장, 기존 라우트·스토어 재사용 | L2 | `reference/design-system/외고반장 PC.dc.html` §3b, 탭별기획 §2 | 3열 렌더·목록↔상세 동기 테스트, 모바일 회귀 없음 |
| 2.5.4b | **Design-first 파운데이션** — 6인 로스터 치환·모델 확장(team/담당/caseCode/체류만료/근거 완성도/agentStage)·중앙 citationStore(id·status·F등급)·EvidenceType 3종(+해시 시드 #4783~91)·토큰 2쌍(draft 보라/detected 시안)+.43 계층·컴포넌트 킷 6종 정합 | L2 | 블루프린트 §3·§4, `Montage 공용 컴포넌트.dc.html` | 기존 테스트 전건(로스터 반영 개정), returned 전이·케이스 단위 승인·F등급 사용 불가 가드레일 테스트, Chip draft/detected 색표 테스트 |
| ✅ 2.5.5 | PC 거버넌스(3c) — 근거 라이브러리(중앙 스토어·KPI 파생·연계 케이스·F등급)·감사 로그(필터·해시·INSERT-only) | L2 | `외고반장 PC.dc.html` §3c, 탭별기획 §4, 블루프린트 §3 — **선행: 2.5.4b** | 내보내기 산출물 해시만(원문 없음) 테스트, 라이브러리 KPI=스토어 파생값 |
| ✅ 2.5.6 | PC 컨트롤 타워(3a) — 파이프라인·KPI·우선 처리 큐·활동/감사 레일 (파이프라인 델타·주간 추이는 mock, 실집계는 M3 데이터로 교체) | L3 | `외고반장 PC.dc.html` §3a, 9단계 P0, 블루프린트 §2(C10: 고위험 행 액션은 "검토") | 큐 정렬(위험×D-day) deterministic 테스트, KPI=스토어 파생값 |

## M2.6 — 모바일 승인 큐 개편 (Mobile.dc.html 2a~2d 채택)

> 근거: `reference/design-system/외고반장 Mobile.dc.html` + `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md`(§1 채택 맵·§2 교정 3건·§5 라우팅). 2026-07-11 사용자 지시로 기존 '보류'를 대체. **선행: 2.5.4b.**
> 데모 대본(8단계 3막) 개정 필요 — 스트리밍 게이트 → 체크리스트 게이트(블루프린트 §2). 사용자 확인 항목.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.6.1 | M1 브리핑 홈 개편(2a): 파이프라인 스탯 로우·"내가 처리할 승인 N건" 카드(단일 "검토" CTA)·"에이전트 진행 중" 리스트 — 커맨드바 존치 | L2 | Mobile.dc.html §2a, 블루프린트 §1 | 2a 카피 렌더 테스트, 카드 CTA 1개 테스트, 기존 5상태 테스트 개정 통과 |
| 2.6.2 | 케이스 상세 전면 페이지(2b): 바텀시트 대체 — 왜 확인·누락 서류·연결 근거·초안 VN/KR·"검토 계속" | L2 | Mobile.dc.html §2b | 전면 페이지 렌더, 검토 계속→승인 페이지 이동 테스트, PC 워크벤치 회귀 없음 |
| 2.6.3 | 승인 체크리스트 페이지(2c): 필수 4항목 게이트·의견/반려 사유·승인/반려(returned 전이) — 배너 문구는 정본 교정(C1) | L2 | Mobile.dc.html §2c, 블루프린트 §2 | 체크리스트 미완 시 승인 disabled, citation-0 잠금 유지, 반려 사유 evidence 기록 테스트, E2E(1.6) 개편 흐름 갱신 |
| 2.6.4 | 승인 이력 페이지(2d): `/case/:id/history` 신설 — 6노드 타임라인·해시·소요시간, 노드 색은 §4.2 정본(C9: 사람 결정만 primary) | L2 | Mobile.dc.html §2d, 탭별기획 §4.2 | 사람 결정 노드만 primary 테스트, 해시만 표시(원문 없음) 테스트 |

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
R1(목 세계 플로우 완결)부터는 각 태스크를 착수 시 이 문서 M1~M4.7 형식으로 개별 승격한다.

## R1 — 목 세계 안에서 플로우 완결 (2026-07-17, `plans/NEXT_ROADMAP_2026-07-16.md` §2 R1 승격)

백엔드 없이 가능한 제품 완성도 — 지금까지 입력을 받고도 버리던 지점(회사 프로필·온보딩 근로자·
CSV·커맨드 바·초안 수정·사장님 리포트)을 실제 상태로 이어 붙인다. 0.5(케이스 타임라인 스토어
승격)가 R1.3의 선행 조건이었는데, R0가 이 브랜치에 문서로만 반영되고 실제 코드는 다른 브랜치
(`claude/next-roadmap-2026-07-16-ca88d8`, 커밋 `4de7ea6`)에만 있던 것을 착수 전 cherry-pick으로
반영해 바로잡았다(문서·코드 불일치 자체가 R0가 원래 없애려던 종류의 문제였다).

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 1.1 | 회사 프로필 슬롯 | L1 | NEXT_ROADMAP 1.1, M-8 | `companyStore.profile` 추가, 온보딩 O3 입력이 완료 시 반영되어 홈(`BriefingHomePage`)·케이스 목록(`CaseListPage`) 헤더의 회사명이 그 값을 따르는 테스트 통과 |
| ✅ 1.2 | 온보딩 근로자 → 실제 케이스 생성 | L1 | NEXT_ROADMAP 1.2, M-8 | O4 입력값이 `lib/csvUpload.workerToCard`(CSV와 동일 데이터 계약, `onboard-` 접두)로 실제 `CaseCard`가 되어 caseStore에 반영되는 테스트 통과. 데모 6인 로스터는 그대로 유지(비파괴) |
| ✅ 1.3 | 케이스 타임라인 런타임 이벤트 반영 | L1 | NEXT_ROADMAP 1.3, D-3 | R0.5(cherry-pick으로 확보)가 이미 충족 — `CaseWorkbench.CaseTimeline`이 `lib/audit.caseTimelineActivity`로 `package_reply`·`interpretation_confirmed`를 실시간 병합함을 재확인(신규 코드 없음, 회귀 테스트로 검증) |
| ✅ 1.4 | 승인 완료 → 발송 큐 자동 연동 | L2 | NEXT_ROADMAP 1.4, M-2 | 고정 `DISPATCH_QUEUE` → `lib/dispatch.deriveDispatchQueue`(approvalStore+evidenceStore 파생)로 교체, actionId를 실제 승인 파이프라인(`nguyen-approve` 등)과 통일, "승인된 것만 도착" 구조적 보장 테스트 통과 |
| ✅ 1.5 | CSV 실제 파일 파싱 | L1 | NEXT_ROADMAP 1.5, M-5 | `lib/csvUpload.parseCsvText` 신설(파싱 즉시 `maskId()` 마스킹) + `CsvUploadWorkbench`가 실제 파일 선택·드래그앤드롭을 처리, `validateRows` 재사용 테스트 통과 |
| ✅ 1.6 | 커맨드 바 최소 매핑 | L1 | NEXT_ROADMAP 1.6, M-7 | `lib/commandBar.resolveCommandRunKey` 신설(워커명 키워드 → 실제 승인 런, 미매칭 시 `#4797` 폴백) + 추천 칩 클릭 시 즉시 제출 테스트 통과 |
| ✅ 1.7 | 초안 수정 요청 개선 | L1 | NEXT_ROADMAP 1.7, M-9 | `DraftPage` 수정 요청 시트가 `revisedText` 고정 토글 대신 편집 가능한 textarea(제안값으로 미리 채움) → 사용자가 고친 문구가 그대로 반영되는 테스트 통과 |
| ✅ 1.8 | 사장님 리포트 파생화 | L1 | NEXT_ROADMAP 1.8, M-10 | `lib/ownerReport.deriveMonthlyReport` 신설(처리한 케이스·사전 감지·승인 없는 발송을 caseStore/evidenceStore에서 파생) — 평균 승인 소요만 D-6(실벽시계·데모 날짜 혼용) 사유로 2.5.6과 동일하게 mock 유지 |

**R1 완료(2026-07-17).** `npm run verify`(typecheck→lint→test 442건→build) 전부 PASS, 브라우저
실검증(온보딩 회사명·근로자 커스텀 입력→홈/케이스 반영, CSV 실파일 업로드→마스킹·등록, 케이스
승인→발송 큐 자동 등장→실행, 커맨드 바 키워드 라우팅, 초안 수정 편집·반영, 사장님 리포트
0건→승인 후 실시간 갱신) 완료. R2(백엔드 배선)는 별도 세션에서 순차 진행한다.

## R2 — 백엔드 배선: API 클라이언트 + 인증 + 읽기 API (2026-07-17, `plans/NEXT_ROADMAP_2026-07-16.md` §2 R2 승격)

R1(목 세계 플로우 완결)까지는 프론트가 fetch 0건인 순수 mock 상태였다. 이 세션은 그 접속점을
연다 — mock이 진실의 원천이던 것을 backend/DB로 옮기되, `VITE_USE_REAL_API` 플래그가 꺼진
기본 상태에서는 지금까지와 100% 동일하게 동작해야 한다는 것이 하드 제약이었다(플래그를 켠
상태만 새 코드 경로를 탄다). 사용자가 이번 세션 범위로 **2.1~2.3**을 선택했다 — 2.4(승인
결정 배선)·2.5(evidence 서버 영속화)·2.6(행정사 링크 서버 강제)는 다음 세션.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 2.1 | API 클라이언트 계층 | L1 | NEXT_ROADMAP 2.1 | `src/lib/api/config.ts`(`API_BASE_URL`·`USE_REAL_API` 플래그, 기본 off)·`client.ts`(`apiFetch<T>` — Bearer 첨부·JSON 파싱·비2xx `ApiError` throw) 신설. 기존 화면 변경 없음(순수 인프라) — 단위 테스트 4건 |
| ✅ 2.2 | 인증 배선 | L2 | NEXT_ROADMAP 2.2, M-4·M-6 | 백엔드 `GET /api/v1/auth/me`(활성 소속 도출) + `CORSMiddleware`(`:5173` 허용) 신설. 프론트 `sessionStore`(persist)·`lib/api/auth.ts`·`lib/auth.ts`(`useAuthActions`) 신설. `StepPhoneAuth`가 `USE_REAL_API`일 때 실제 전화번호 입력+OTP 왕복으로 세션을 확립하고 `roleStore.setRole(membership.role)`까지 반영("역할 파생 절충안" — 기존 데모 순환 토글은 그대로 유지, 실서버엔 viewer 계정이 없어 완전 대체는 범위 밖) |
| ✅ 2.3 | 읽기 API 신규 구현 + 프론트 배선 | **L3** | NEXT_ROADMAP 2.3, M-6 | 백엔드에 케이스/브리핑/스레드 읽기 엔드포인트 신규 구현(`GET /api/v1/cases`·`/briefings/latest`·`/threads`·`/threads/{id}`, `get_current_membership`으로 company 스코프, `db/schema.sql` 계약 준수) + 각 도메인 테스트. 프론트 `lib/api/{cases,briefings,threads}.ts` DTO→도메인 타입 어댑터 + `lib/dataSeed.ts`(8개 이상 화면에 중복되던 "스토어 비어있으면 픽스처로 시드" `useEffect`를 `useSeedCases`/`useSeedThreads`/`useSeedThreadDetail` 공용 훅으로 통합, 내부에서 `USE_REAL_API` 분기) 신설 — 13개 화면 전부 이 훅으로 배선 |

**R2(2.1~2.3) 완료(2026-07-17).** 백엔드 `uv run pytest` 124건 PASS, 프론트 `npm run verify`
(typecheck→lint→test 483건→build) PASS(플래그 기본 off — 회귀 0건), 브라우저 실통합 검증
(`VITE_USE_REAL_API=true` + 로컬 백엔드, 데모 전화번호 010-0000-0001 OTP 로그인 → 케이스
목록/컨트롤 타워/스레드가 시드 데이터(`db/seed_demo.sql`)로 실제 렌더) 완료. 검증 중 발견한
버그 1건 즉시 수정: `dataSeed.ts`의 fetch 호출에 `.catch()`가 없어 로그인 전(401) 상황에서
처리되지 않은 프로미스 거부가 발생 — 콘솔 경고로만 남기고 스토어는 비운 채 두도록 수정.
2.4(승인 결정 배선)·2.5(evidence 서버 영속화)·2.6(행정사 링크 서버 강제)는 다음 세션.

## 백엔드 접속점 (이후 — 별도 계획)

- mockApi → 별도 승인된 backend 이식으로 교체. `db/schema.sql`의 복합 FK·CHECK·trigger 계약과 `src/types.ts`를 함께 이식하며, 인증 principal·본인확인·delegation 검증 전에는 승인 결정 endpoint를 만들지 않는다.
- runEngine 각본 → LangGraph createAgent 스트리밍으로 교체 (RunConfig 인터페이스 유지)
- 발송 어댑터·알림톡은 계속 범위 밖 (승인 기반 어댑터, PRD Sprint 6)¹

¹ outbox(발송 대기열)+`SmsAdapter`+응답 링크 인바운드까지의 로드맵은 `docs/MESSAGING_CHANNELS.md` §5(단계 로드맵)에 정리돼 있다 — 이 저장소는 현재 ①(프론트 Message 도메인 + `MockAdapter`)까지만.
