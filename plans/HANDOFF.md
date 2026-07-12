# HANDOFF — 세션 인수인계 기록

> 규칙: 태스크를 끝내거나 컨텍스트 40%에 도달해 세션을 넘길 때, 에이전트가 아래 형식으로 **맨 위에** 추가한다.
> 새 세션의 첫 행동: 이 파일의 최신 항목 1개 + ROADMAP의 다음 태스크를 읽는 것. (전체 히스토리 로드 금지)

---

## 형식

```
### [날짜] 태스크 번호 — 상태 (완료/중단)
- 한 일:
- 남은 일 / 중단 지점:
- 결정 사항 (다음 세션이 알아야 할 것):
- verify 상태: PASS/FAIL(원인)
- 지도/규칙 갱신: (했으면 무엇을)
```

---

### [2026-07-11] 2.5.5 — 완료 (PC 거버넌스 §3c)
- 한 일: `reference/design-system/외고반장 PC.dc.html` §3c 이식 — 데스크톱 전용 2열. **좌 근거 라이브러리**: `citationStore`(2.5.4b) 구동, KPI 5종(전체/공식 A·B/최신성/검토 필요/부족 stale)을 `citationKpis` 셀렉터로 파생(하드코딩 아님), 테이블(등급 칩·제목·출처·최신성·상태 칩·연계 케이스 수=`linkedCaseCount(CASE_SHEETS)`), F등급=critical 톤(사용 불가). **우 감사 로그**: `mergedAuditLog`(시드+런타임 병합, id 중복 런타임 우선, 최신순) + 필터 칩(전체/위험 탐지/승인/내보내기, `AUDIT_FILTERS` 술어), ref·타입 칩·행위자·해시(monospace), 하단 "INSERT-only · 원문 PII 미저장". 감사 셰이핑은 `src/lib/audit.ts`로 분리(M8 2.3 재사용 예정). 라우팅: `/evidence` → `EvidencePage`가 `useIsDesktop`으로 분기(데스크톱=GovernancePage, 모바일=M8 placeholder 유지).
- 남은 일 / 중단 지점: 없음. 근거 등록 CTA·정책 룰 엔진은 post-MVP(§3c 헤더 문구대로 라이브러리는 읽기 전용). 다음은 2.5.6 PC 컨트롤 타워(§3a) — `pipelineStats`(2.5.4b)·`AUDIT_TYPE_*`(2.5.5) 재사용, C10 교정(고위험 행 액션 "검토") 반영. 데스크톱 nav 라벨은 아직 Shell의 브리핑/케이스/메시지/기록 — 디자인 PC nav(컨트롤 타워/케이스/거버넌스/설정)와 다르며 2.5.6에서 정렬 검토.
- 결정 사항 (다음 세션이 알아야 할 것): ① 감사 로그의 시드 병합은 `mergedAuditLog`(audit.ts) 하나로 통일 — CaseHistoryPage(2d)와 M8(2.3)도 이 함수를 써 화면마다 다른 이력이 안 나오게 한다. ② `AUDIT_TYPE_LABEL`/`AUDIT_TYPE_TONE`은 전 EvidenceType을 커버(테스트로 강제) — 새 타입 추가 시 두 맵에 반드시 함께 추가. ③ 데스크톱 화면은 전부 `useIsDesktop` 렌더 분기 + Shell lg 헤더(h-16) 아래 `h-[calc(100dvh-4rem)]` 채움 패턴.
- verify 상태: PASS (typecheck 0, lint 0, **42 files/232 tests**, build OK). 브라우저 실측(1280px): 2열·KPI 파생값(전체 9·공식 7·최신성 8·검토 2·부족 1)·라이브러리 9행·감사 7건·해시 6개, 필터(내보내기→1건 export만/위험→risk만) 동작, 콘솔 에러 0. 모바일(375px): 거버넌스 미마운트, M8 placeholder 유지.
- 지도/규칙 갱신: ROADMAP 2.5.5 ✅ 표기.

---

### [2026-07-11] M2.6 코드리뷰 수정 — 완료 (승인 생애주기 버그 클러스터)
- 한 일: 8앵글 PR 리뷰(파인더 7종) 확정 버그를 근본 교정. **근본 원인**: ApprovePage가 승인을 일회성으로 인라인 처리 → 크래시·감사 오기록·가드레일 우회. **공유 유닛 신설** `src/lib/approval.ts`(`useApprovalActions`: approve/reject/reopenForReview + canApproveCase/approvalRefFor/isCitationLocked + CURRENT_USER). 교정: ① **반려 케이스 재승인 크래시**(A1/B2) — ensurePending이 terminal approval을 pending으로 리셋, 반려 카드는 검토 계속 시 returned→approval_pending 재개. ② **고위험 blocked 승인 우회**(A2/B3/F3) — canApproveCase가 상태 전이 합법성으로 CTA 게이트, 2b는 "행정사 전달 준비(승인 후)"로 분기(검토 계속 없음), ApprovePage는 guardNote+승인 비활성. ③ **반려가 '최종 승인'으로 감사 기록**(A3) — EvidenceType `approval_rejected` 신설, 이력에서 '반려'(비-primary)로 표기, 승인 완료 배너·판단 기록 저장 노드는 approval_decided에만. ④ **evidenceRef #4789 하드코딩**(F1) — approvalRefFor로 케이스별 파생. ⑤ **agentStage 미전진**(A4) — 승인 시 executed로 upsert(파이프라인·큐 정합). ⑥ **더블탭 중복 evidence**(A5) — evidenceStore append id 중복 방지. ⑦ **caseStage F등급 미필터**(C1) — usableCitations 경유. ⑧ **프로액티브 런 재생 링크 소실**(B5) — 2b 판단 기록 #을 /run/:id 링크로 복원. ⑨ **RunPage 죽은 caseId 분기**(B/altitude) — runId 전용으로 정리. ⑩ **중복 제거**(D): BackHeader(3화면), draftForCase(4화면), dDayTextClass(2화면), pipelineStats 5단계 통합. ⑪ accent 임의값(G2)→accent-primary. ⑫ 큐 파랑 CTA(G1)는 디자인 §2a 채택 예외로 GOTCHAS 명문화.
- 남은 일 / 중단 지점: 없음(리뷰 확정건 전부). 저순위 미처리(의도적): 오프라인 승인 가드(B1)·읽기전용 검토 오프라인 비활성(B4) — 오프라인은 런타임 미배선(백엔드 접속점 몫)이라 배선과 함께 복원. actor 문자열 통합은 CURRENT_USER로 신규 경로만 적용(시드는 그대로).
- 결정 사항 (다음 세션이 알아야 할 것): ① 승인/반려 결정은 반드시 `useApprovalActions`를 통한다 — 화면에서 requestApproval/decide/transition/append를 인라인 복제 금지(PC 워크벤치 승인 붙일 때도 이 유닛 사용). ② 반려는 `approval_rejected`, 승인은 `approval_decided` — 감사 노드 구분의 기준. ③ 고위험(blocked)은 canApproveCase가 false라 앱 승인 불가 — 행정사 전달(2.4)이 정식 경로. ④ evidenceStore.append는 id 중복 시 no-op(더블탭 안전).
- verify 상태: PASS(typecheck 0, lint 0, **40 files/220 tests** — 신규 회귀 테스트: approval.test.ts 4종 + approvalFlow 3종(반려 이력·재승인·고위험). 병렬 경합 플레이크는 setup.ts asyncUtilTimeout 15s로 근본 해소, 2회 연속 전건 통과). 브라우저 실측: batbayar 고위험 전달 분기·nguyen 반려→returned 칩·콘솔 에러 0.
- 지도/규칙 갱신: `docs/GOTCHAS.md`(파랑 CTA 큐 예외), `src/test/setup.ts`(asyncUtilTimeout).

---

### [2026-07-11] 디자인 원본 저장소 고정 — 완료 (PR 리뷰 반영)
- 한 일: PR 리뷰 지적("외부 디자인 원본을 저장소 안의 재현 가능한 스펙으로 고정한 뒤 병합하는 편이 안전")을 반영. `rules/design.md`·ROADMAP 2.5.4~2.5.6·`.claude/agents/ui-matcher.md`가 전부 claude.ai/design 라이브 프로젝트(`bd0fd8f8-615f-48e9-875b-eb5c9e9b398d`)만 가리키고 있어, 그 프로젝트가 바뀌거나 접근 불가해지면 스펙 근거가 사라지는 구조였다. `reference/design-system/`에 4개 파일을 그대로 고정: `montage-wanted/colors_and_type.css`(원본 CSS — 기존 `외고반장_통합/09_.../colors_and_type.css` 미러와 sha256 비교로 100% 일치 확인, 드리프트 없었음), `montage-wanted/source-rules-design.md`(디자인 프로젝트 자체 rules/design.md 원문 — 우리 저장소의 `rules/design.md`는 이걸 각색한 것), `외고반장 PC.dc.html`(190KB, ROADMAP 2.5.4~2.5.6의 1차 스펙), `외고반장 Mobile.dc.html`(85KB, 채택 보류된 개편안 — 참고 고정만). `rules/design.md`·`plans/ROADMAP.md`(M2.5 블록쿼트 + 2.5.4/5/6 스펙 컬럼)·`docs/SPEC_INDEX.md`·`docs/DESIGN_SYNC_AUDIT_2026-07-11.md`·`.claude/agents/ui-matcher.md`의 참조를 전부 고정 사본 경로로 갱신.
- 남은 일 / 중단 지점: 없음. 디자인 프로젝트가 실제로 바뀌면 다시 `get_file`로 받아 `reference/design-system/`을 갱신하고 이 파일 + `reference/design-system/README.md`에 남긴다(README에 절차 명시).
- 결정 사항 (다음 세션이 알아야 할 것): 이제부터 디자인 근거를 인용할 때 claude.ai/design 프로젝트 URL이 아니라 `reference/design-system/` 안의 고정 파일 경로로 인용한다. `.dc.html` 파일은 디자인 도구 전용 캔버스 마크업이라 브라우저로 그대로 열어도 프로덕션 렌더링과 다를 수 있음(값·구조 참고용).
- verify 상태: PASS — 문서·reference 파일만 추가/수정(src/ 무변경)이라 `npm run verify` 결과는 직전 항목(2.5.3)과 동일(typecheck 0, lint 0, 38 files/196 tests, build OK).
- 지도/규칙 갱신: `rules/design.md`(출처 라인), `plans/ROADMAP.md`(M2.5 블록쿼트 + 2.5.4~2.5.6 스펙 컬럼), `docs/SPEC_INDEX.md`, `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`(§6에 재현성 보강 항목 추가), `.claude/agents/ui-matcher.md`(기준 문구) — 전부 이 세션에서 갱신.

---

### [2026-07-11] M2.6 (2.6.1~2.6.4) — 완료 (모바일 승인 큐 개편)
- 한 일: Mobile.dc.html §2a~2d 전면 이식 — **"카드에서는 검토만, 승인은 체크리스트 화면에서"**. ① **2.6.1 홈(2a)**: `BriefingHeader`(오늘 브리핑 제목+날짜·사업장+벨), `PipelineStatRow`(누적 깔때기 6·5·4·3 + 실행(주) 12 — `lib/pipeline.ts` 파생+`EXECUTED_WEEKLY_MOCK`), `ApprovalCard` 단일 "검토" CTA로 재설계(2CTA 제거, returned 보완 칩 추가), `AgentProgressList` 신설, 인사문장·SummaryStatRow 제거(컴포넌트 삭제), 커맨드바 존치. ② **2.6.2 검토(2b)**: `CaseReviewPage` 신설 — `/case/:id` 모바일이 바텀시트 대신 전면 페이지(케이스 헤드·왜 확인·누락 서류·연결 근거·초안 VN/KR 인라인 토글·검토 계속). `CaseSheet` 컴포넌트 삭제(워크벤치·검토 페이지가 대체). 진입 시 `review_started` evidence(중복 가드). **기본 언어=근로자 언어(VN)** — 브라우저 검증 중 발견해 교정. ③ **2.6.3 승인(2c)**: `ApprovePage` 신설 — `/case/:id/approve`에서 RunPage 대체. 게이트 교체: 필수 체크리스트 4/4 + citation-0 잠금(이중). 배너 제목은 정본 상수(`SAFETY_NOTICE_TEXT` — SafetyNotice에서 export, C1 교정). 반려하기 = 사유와 함께 `decide(rejected, reason)` + `approval_pending→returned` 전이 + evidence. 승인 = `checklist_completed`+`approval_decided`(#4789, 김담당 (본인)) → 2d 이동. ④ **2.6.4 이력(2d)**: `CaseHistoryPage` + `/case/:id/history` 라우트 신설 — 결과 카드+생애 타임라인(시드 표시 병합)+정적 "발송 실행 (mock) · 예정" 노드, **사람 결정 노드만 primary**(C9 교정), 하단 "모든 판단·승인은 Evidence Log에 기록됩니다.".
- 남은 일 / 중단 지점: 없음(M2.6 완료). 다음은 2.5.5 PC 거버넌스(citationStore 준비돼 있음) → 2.5.6 → 2.4·2.2·2.3. 참고: RunPage의 `caseId → approval config` 분기는 이제 도달 불가 경로(라우트가 ApprovePage로 교체됨) — /run/:runId 전용으로 남아 있으며 정리(단순화)는 후속 리팩터 후보.
- 결정 사항 (다음 세션이 알아야 할 것): ① 성급한 승인 방지 게이트 = **체크리스트 4/4**(구 스트리밍 게이트 대체, GOTCHAS 개정 확정). 데모 3막 대본은 이 게이트 기준으로 개정 필요(블루프린트 §2 — 사용자 확인 항목). ② evidenceStore는 비어 시작(런타임 전용)이고 시드는 **표시 시점 병합**(CaseHistoryPage) — 시드 상주는 M8(2.3) 몫. ③ 2d "승인 요청 생성" 노드는 시드에서 온다 — 새 케이스 승인 플로우를 추가하면 EVIDENCE_SEED에 approval_requested를 함께 넣을 것.
- verify 상태: PASS(typecheck 0, lint 0, **39 files/212 tests**, build OK — SummaryStatRow/CaseSheet 테스트 삭제, E2E 신규 깔때기 2본으로 재작성). 브라우저 실측(375px): 홈 파이프라인 6·5·4·3·12 디자인 일치, 검토 버튼 3개·카드 승인 버튼 0개, 2b(VN 기본 초안·승인 버튼 없음) → 2c(4/4 전 승인 disabled·정본 배너) → 2d(#4789·human 노드 primary·mock 발송 예정) 전 구간 통과, 콘솔 에러 0.
- 지도/규칙 갱신: `docs/GOTCHAS.md`(카드 CTA 규칙 개정 확정), `docs/ARCHITECTURE.md` §3(라우트 3행), `.claude/agents/ui-matcher.md`(모바일 기준 = Mobile.dc.html 2a~2d + 교정 3건).

---

### [2026-07-11] 2.5.4b — 완료 (Design-first 파운데이션)
- 한 일: 블루프린트 §3·§4 전면 구현. **① 6인 로스터 치환**(fixtures 전면 재작성 — Batbayar E./Nguyen Van A/Siti R./Tran Thi H./Rahmat P./Oyunaa T., mohammad·hiring 제거, title은 업무 단위로 분리, 사업장명 그린푸드 제조·기준일 07.10). **② 타입 확장** — WorkerRef.team, CaseCard.caseCode/assignee/stayExpiryDate/evidenceCompleteness/agentStage, CaseState.returned(+caseStore 전이 표), CitationGrade.F, EvidenceType 3종(review_started/checklist_completed/exported), Approval.reason(+decide 4번째 인자). **③ 중앙 근거 라이브러리** — `src/mocks/citations.ts`(cit_001~cit_021, §3c 8행+§2d 1행) + `citationStore`(KPI·연계 수 셀렉터 파생, `usableCitations` F 제외 필터 — CaseSheet·워크벤치 잠금 판정에 적용). **④ Evidence 시드** — §3c 대역(#4783~#4791)·해시·행위자(김담당 (본인)/system)로 재작성, 커맨드 런 #4790→**#4797** 재번호(디자인에서 #4790=Siti 승인 요청으로 확정). **⑤ 토큰** — chip draft(보라)/detected(시안) 2쌍(+다크), label .43(dim)/.61(subtle) 계층, track. **⑥ 컴포넌트 킷 6종 정합**(Montage 공용 컴포넌트.dc.html) — SafetyNotice 2형(neutral 고정문구 불변+emphasis), OfflineBanner 경고형(+재시도), Skeleton shimmer, StepTimeline 세로형(펄스 링·가드레일 칩), 탭바 비활성 .61+아이콘 3종 교체(IconBriefing/IconFolder/IconClock 신설), BottomSheet 핸들 line 토큰. 화면 반영: ApprovalCard·CaseList 근로자 부제, 워크벤치 팀 부제·구조화 메타·근거 완성도 진행바·이름 검색.
- 남은 일 / 중단 지점: 없음. 다음은 블루프린트 §8 순서 — **M2.6(모바일 2a→2b→2c→2d)** → 2.5.5 → 2.5.6. GOTCHAS의 "카드 CTA 2개" 규칙은 M2.6에서 1개("검토")로 개정 예고만 해둠(그 전까지 2개 유지).
- 결정 사항 (다음 세션이 알아야 할 것): ① 케이스 근거는 반드시 `libCitation('cit_*')` 참조로 연결한다 — 값 복제 금지(라이브러리가 단일 출처, citationStore 테스트가 id 보유를 강제). ② `agentStage`가 있으면 스테퍼·파이프라인 파생에서 상태보다 우선한다. ③ 텍스트 계층: 부제·비활성 탭=`text-subtle`(.61), 타임스탬프·해시=`text-dim`(.43) — muted(.88)는 본문 보조용. ④ 반려는 approval_pending↔returned 왕복만 허용(가드레일 테스트 있음).
- verify 상태: PASS(typecheck 0, lint 0, **41 files/223 tests** — 신규 10개 포함, build OK). 브라우저 실측: 모바일 홈(6건 인사·Batbayar 히어로·근로자 부제·탭바 비활성 rgba(55,56,60,0.61)+아이콘 4종), 데스크톱 워크벤치(6행 큐 순서·팀 부제·meta "E-9 · 포장팀 · 인도네시아 · case_003"), /run/4797 커맨드 런 정상, 콘솔 에러 0.
- 지도/규칙 갱신: `rules/design.md` §5(파이프라인 칩 2행+F등급)·§6(킷 6종 스펙 명시), `docs/GOTCHAS.md`(케이스 단위 승인·F등급 추가, CTA 규칙 개정 예고).

---

### [2026-07-11] 2.5.4 — 완료 (+ Design-first 블루프린트 수립)
- 한 일: **PC 케이스 워크벤치(3열)** 구현 — `reference/design-system/외고반장 PC.dc.html` §3b 기준. `src/features/cases/CaseWorkbench.tsx`(목록 레일 290px·상세·AI/근거 레일 340px, 진행 스테퍼·서류 체크리스트·다국어 초안·타임라인·승인/전달 상태·행정사 전달 잠금·가드레일 문구 2종) + `CaseWorkbenchPage.tsx`(컨테이너, /cases·/case/:id 공유) + `src/lib/useIsDesktop.ts`(matchMedia+resize 이중 리스너, jsdom 기본 false) + `src/lib/caseStage.ts`(진행/전달 단계 파생 — 발송 mock 미도달 가드) + 토큰 3종(shadow rail-active/rail-focus/step-current). 필터·그룹·정렬은 `lib/cases` selector 재사용, CTA는 데이터 구동 라벨 그대로, citation-0 잠금 동일 적용. **오래된 테스트 플레이크 근본 수정**: `/case/:caseId` loader 비동기 커밋 경합 — `CaseListPage.test.tsx` scrim 대기와 신규 테스트 모두 DOM 기준 `findBy*`(+5s)로 전환.
- 남은 일 / 중단 지점: 없음(2.5.4 자체는). 단, **디자인 소스 채택 지시(2026-07-11)** 로 후속 전체 설계가 `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md`에 수립됨 — 다음 착수는 블루프린트 §8 순서: **2.5.4b 파운데이션**(6인 로스터·모델 확장·citationStore·토큰 2쌍·컴포넌트 킷 6종) → M2.6(모바일 2a~2d) → 2.5.5 → 2.5.6. 워크벤치의 로스터·담당·근거 완성도 표시는 2.5.4b에서 소급 적용.
- 결정 사항 (다음 세션이 알아야 할 것): ① 데스크톱 분기는 CSS hidden이 아니라 `useIsDesktop` **렌더 분기** — 모바일에서 데스크톱 트리가 마운트되지 않아 기존 테스트·접근성 트리가 오염되지 않는다. 새 PC 화면(2.5.5/2.5.6)도 같은 패턴을 쓸 것. ② 선택 상태의 진실은 URL(/case/:id) — 검색으로 레일에서 걸러져도 상세는 URL 케이스를 유지. ③ returnTo는 반드시 `ROUTES.cases()`로 생성(CaseSheetPage의 safeCaseListReturnTo 화이트리스트 통과 조건).
- verify 상태: PASS(typecheck 0, lint 0, **40 files/213 tests**, build OK — 플레이크 수정 후 2회 연속 전건 통과). 브라우저 실측(1280px): 3열 렌더·행 클릭→URL/상세 동기·선택 인디케이터·다크 모드 토큰 전환·필터 프리셋(aria-pressed)·스테퍼/전달 단계 라벨 디자인 원문 일치 확인, 콘솔 에러 0. 모바일(375px) 리로드: 워크벤치 미마운트+바텀시트 플로우 무결. **주의: 멀티에이전트 검증 워크플로우는 2회 모두 외부 요인(중단 1회, 서브에이전트 세션 한도 1회 — 17:40 리셋)으로 실패해 동일 항목을 인라인 수행함**(정적 grep 배터리·코드 리뷰·verify — 전부 클린).
- 지도/규칙 갱신: `plans/ROADMAP.md`에 블루프린트 §6 반영(2.5.4b·M2.6 신설, 2.5.5/2.5.6/2.4 스펙 보강). GOTCHAS·rules/design.md 개정은 2.5.4b 구현과 함께(블루프린트 §7).

---

### [2026-07-11] 2.5.3 — 완료
- 한 일: 기존 화면 13개 파일의 타이포그래피를 Montage v2 타입 스케일(`text-heading1`/`heading2`/`body1`/`body2`/`label1`/`caption1`, tailwind.config.js에 2.5.1에서 이미 등록돼 있던 유틸리티)로 전환. 역할 분류 규칙: 화면 최상단 h1/h2 제목→heading2(20px, CaseListScreen은 24→20 보정·DonePage/DraftPage/RunScreen은 18→20 승격으로 통일), 카드/시트 h3 제목→body1(16px), 인사문장·빈상태 큰 강조→heading1(22px), 서술형 문장(설명·안내·에러 메시지)→body2(15px), 버튼/칩/행 라벨 같은 UI 크롬→label1(14px), 캡션·타임스탬프→caption1(12px). 기존 font-weight/leading-* 클래스는 그대로 유지(사이즈 토큰만 교체). Workflow로 13개 파일 병렬 치환 + 적대적 감사 에이전트를 돌려 놓친 3곳(`CaseSheet.tsx:114`, `DonePage.tsx:31`, `DraftPage.tsx:69` — 전부 "text-sm" 잔존)을 찾아 직접 수정. `.claude/agents/ui-matcher.md`를 prototype_v3 기준에서 디자인 프로젝트(+ Chip tone 명칭·타이포·아웃라인 체크 항목 추가)로 교체하면서, 초안이 잘못 인용한 `외고반장 Mobile.dc.html`(보류 결정된 모바일 개편안)을 "기준 아님"으로 정정.
- 남은 일 / 중단 지점: 없음 — M2.5는 2.5.1~2.5.3 전부 완료. 다음은 ROADMAP 2.5.4(PC 케이스 워크벤치) 또는 2.2(메시지 탭).
- 결정 사항 (다음 세션이 알아야 할 것): 화면 h1/h2는 이제 전부 heading2(20px)로 통일한다 — 기존처럼 화면마다 다른 크기(18/20/24px)를 쓰지 않는다. 새 화면 타이포는 이 6단계 스케일 중에서 고르고, `text-lg`/`text-xl`/`text-2xl` 같은 임시 크기는 (Button.tsx/Chip.tsx 등 컴포넌트 자체 내부 스타일 제외) 다시 쓰지 않는다.
- verify 상태: PASS (`npm run verify`: typecheck 0, lint 0, 38 files/196 tests 통과, build OK). 브라우저(Vite dev) 실측으로 heading2(20/28px, -0.24px 자간)·heading1(22/30px)·body1(16/22px, 기존 leading-snug 유지) 계산값이 토큰과 일치함을 확인, 콘솔 에러 없음.
- 지도/규칙 갱신: `rules/design.md` 상단 배너를 "2.5.1·2.5.2·2.5.3 완료"로 갱신. `.claude/agents/ui-matcher.md` 전면 교체(위 참조).

---

### [2026-07-11] 2.5.1·2.5.2 — 완료
- 한 일:
  - **2.5.1**: `src/styles/tokens.css`를 Montage(Wanted) v2 atomic+semantic 토큰으로 전면 교체(라이트 기본 + `[data-theme="dark"]`), `tailwind.config.js`는 유틸리티 이름(`canvas`/`ink`/`critical`/`rounded-in`/`shadow-card` 등)을 그대로 두고 `var()` 대상만 재배선해 20여개 소비 파일 무변경 색상 전환 달성. `--fs-pc-*`(PC 밀도 타입램프)·Montage 타입 스케일(`heading1`~`caption1`)을 Tailwind `fontSize`에 등록(아직 어느 화면도 적용 안 함, 2.5.3·2.5.4+ 몫). **라이트/다크 토글 UI 신규 구현**: `src/stores/themeStore.ts`(zustand, localStorage 영속 + `prefers-color-scheme` 폴백) + `Shell.tsx`에 토글 버튼(PC 헤더·모바일 우상단 고정) + `icons.tsx`에 `IconSun`/`IconMoon` 추가. 브라우저 실사용 검증 중 **Chip 배경이 라이트 전용 고정 hex라 다크 배경에서 붕 뜨는 문제**를 발견해 `chip-*-bg`/`-fg`에 다크 전용 오버라이드(옅은 rgba 틴트 + Montage 자체 다크 상태색) 추가.
  - **2.5.2**: `src/components/Badge.tsx`→`Chip.tsx`, `src/lib/badgeTone.ts`→`chipTone.ts` 개명. **톤 이름을 값과 함께 새로 설계**(`rules/design.md` §5 기준) — v1의 `pending`(amber)/`info`(blue)라는 모호한 이름을 없애고 `approval`(승인 필요=블루)/`medium`(MEDIUM 위험도=흐린 오렌지)으로 분리(v1은 이 둘의 색이 정반대였다). `src/lib/dday.ts`의 `DDayTone`도 동일하게 `warning`→`high`, `info`→`medium`으로 새로 짬(D-31~90 배지가 파랑에서 흐린 오렌지로 바뀜 — 블루는 이제 "승인 필요" 전용). `Button.tsx` outline 배리언트를 `border` → `shadow-outline`(inset box-shadow)으로 교체, 사이즈별 라디우스(`rounded-in` 10px/`rounded-btn-sm` 8px) 도입. 소비 파일 전부 갱신: `DraftPage`/`DonePage`/`CaseListScreen`/`ApprovalCard`/`CaseSheet`/`BriefingScreen`.
  - **덤으로 발견해 고침**(토큰 마이그레이션 중 같은 파일을 만지다 발견, GOTCHAS 임의값 금지 위반): `CaseListScreen.tsx`의 `rounded-[14px]`/`rounded-[8px]`(임의값) → `rounded-chip`/`rounded-in`, 존재하지 않는 `border-line` 클래스 → `border-hairline`. 같은 파일의 "승인 필요" Chip이 텍스트와 안 맞게 `neutral`(회색) 톤이었던 것을 `approval`(블루)로 정정.
- 남은 일 / 중단 지점: 2.5.3(기존 화면에 Montage 타입 스케일 실제 적용 + `.claude/agents/ui-matcher.md` 기준을 prototype_v3→디자인 프로젝트로 교체)이 남음 — 색상·라디우스·그림자·모션은 이미 전부 v2, 글자 크기만 과거 Tailwind 임시값. `rules/design.md`의 부록 A(v1 요약)는 이미 삭제함(코드에 v1 hex가 더 안 남아 조건 충족). 이 머신엔 Node가 기본 설치돼 있지 않아 포터블 Node(`%LOCALAPPDATA%/nodejs-portable`, PATH는 `~/.bashrc`에 등록됨— 새 대화 세션의 셸에선 안 읽힐 수 있으니 안 되면 `export PATH=".../node-v22.14.0-win-x64:$PATH"` 재실행)로 대체 설치했다.
- 결정 사항 (다음 세션이 알아야 할 것):
  - Chip/DDay 톤 이름 규칙: **'pending'·'info' 같은 모호한 이름은 다시 쓰지 않는다** — 색상표(rules/design.md §5)의 실제 의미를 이름에 반영한다(critical/high/medium/positive/approval/neutral/line).
  - D-31~90 D-day 배지는 이제 파랑이 아니라 흐린 오렌지다(블루는 승인 필요 전용) — 의도된 변경, 되돌리지 말 것.
  - Chip 배경은 라이트/다크 각각 다른 값을 가진다(다크는 rgba 틴트) — 새 톤 추가 시 `[data-theme="dark"]` 블록에도 짝을 넣을 것.
- verify 상태: PASS — `tsc --noEmit` 0, `eslint .` 0, 38 files/196 tests 통과(마이그레이션 전 존재하던 `CaseListPage.test.tsx`의 `bottom-sheet-scrim` 클릭 테스트가 전체 스위트에서 가끔 실패하는 건 파일 단독 실행 시 100% 통과 확인 — 순서 의존 플레이키, 이번 변경과 무관, 미수정), `vite build` OK. 브라우저(Vite dev, localhost:5173)에서 토글 클릭 실측: `data-theme` 전환·`localStorage` 영속·Chip 4종(critical/high/medium/approval) 라이트·다크 양쪽 실제 계산된 색상이 토큰표와 정확히 일치함을 확인.
- 지도/규칙 갱신: `rules/design.md` 상단 배너를 "2.5.1·2.5.2 완료"로 갱신하고 부록 A(v1 토큰 요약) 삭제.

---

### [2026-07-07] 2.1 — 완료 (사후 이기 2026-07-11)
- 한 일: M7 케이스 목록을 `/cases`에 연결 — 필터 칩, 딥링크 프리셋(`?filter=crit|warn|info|approval`), 고정 그룹 순서(승인 대기→즉시 확인→확인 필요→예정→완료(접힘)). 필터·그룹·정렬 로직은 `src/lib/cases.ts` selector로 분리, 화면은 `src/features/cases/`의 `CaseListPage`/`CaseListScreen`. compact 아이템은 CTA 없이 `/case/:caseId`로 진입. (Codex 세션 구현 — PR #2, 커밋 `66e299e`·`e70005f`, 머지 `5531370`)
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 2.2 — 단 M2.5(디자인 시스템 v2 전환) 신설로 2.5.1~2.5.3 선행 권장(ROADMAP 헤더·M2.5 참조).
- 결정 사항 (다음 세션이 알아야 할 것): M7 필터·정렬 로직은 컴포넌트가 아니라 `src/lib/cases.ts` selector를 기준으로 유지한다.
- verify 상태: 당시 세션 기록 PASS(`npm run test:run -- src/lib/cases.test.ts src/features/cases/CaseListPage.test.tsx`), 전체 verify는 별도 최종 검증으로 미룸. 이기 세션(문서 전용, Node 미설치 환경)에서는 재실행 불가.
- 지도/규칙 갱신: 원 기록이 번들 사본 `외고반장_통합/13_클로드코드_구현패키지/plans/HANDOFF.md`에 작성되어 있어 이 파일로 이기함(ROADMAP ✅ 표시도 번들 사본에만 존재). **이후 세션은 반드시 루트 `plans/HANDOFF.md`에 기록할 것.**

---

### [2026-07-07] 1.6 — 완료
- 한 일: M3/M4/M5 승인 해피패스 루프 구현. `src/features/draft/DraftPage.tsx`를 추가해 `/case/:caseId/draft`에서 DRAFT fixture 기반 초안, 언어 토글, 수정 요청 BottomSheet, 수정 반영 후 승인 검토 이동을 제공. `src/features/run/RunPage.tsx`의 approval mode 승인 버튼을 `approvalStore.requestApproval/decide` + `caseStore.transition(caseId, 'human_approved')` + `evidenceStore.append(approval_decided)`에 연결하고 `/done`으로 이동. `src/features/done/DonePage.tsx`를 추가해 “발송 승인 완료” 전용 완료 화면을 렌더하되 실제 카톡/문자/정부 제출은 실행하지 않음을 명시. `ApprovalCard`는 `human_approved` 상태에서 “승인 완료” 배지를 표시. 실제 라우터 기반 통합 테스트 `src/features/approvalFlow.test.tsx`를 추가해 `/case/nguyen` → M2 → M3 → M4 → M5 → M1 상태 반영을 검증.
- 남은 일 / 중단 지점: Playwright 패키지/스크립트는 현재 프로젝트에 없어 ROADMAP의 “playwright E2E”는 Vitest 라우터 통합 테스트로 대체했다. 진짜 브라우저 E2E가 필요하면 Playwright 의존성과 `npm run test:e2e` 스크립트를 별도 태스크로 추가해야 한다. 수정 요청 시트는 고정 “부드럽게 다듬기” 프리셋 1개만 제공한다(자연어 수정 요청/다중 프리셋은 범위 밖).
- 결정 사항: M4 승인 후에도 외부 발송 함수는 만들지 않는다. 승인 결정과 상태 전파만 수행하고, 완료 화면 문구는 “발송 승인 완료”를 사용한다. Evidence 이벤트 타입은 기존 타입 계약에 맞춰 `approval_decided`를 사용한다.
- verify 상태: PASS (`npm run verify`: typecheck 0, lint 0, test 36 files/184 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2·§5·§7에 M3/M5 위치와 1.6 승인 상태 전파를 반영.

---
### [2026-07-06] 1.5 — 완료
- 한 일: L3(협업) 태스크라 `superpowers:brainstorming`으로 시작 — 범위(3모드 한번에 vs approval만 먼저)와 M4/M9 화면 공유 여부를 질문으로 확정한 뒤 설계 스펙(`docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md`) 작성·커밋, 구현 계획(`docs/superpowers/plans/2026-07-06-run-engine-steptimeline.md`, 9태스크) 작성 후 subagent-driven-development로 실행. `src/mocks/runs.ts`의 `RunStepKind`를 공식 5종(thinking/tool_call/guardrail/handoff/replan)으로 정리하고 M0.5의 로컬 `'wait'` 확장 제거("승인 대기"는 RunStep이 아니라 런의 종착점), command(#4790)·replay(#4788) config 2건 추가. `src/lib/runEngine.ts`(React 비의존 `executeRun` — 430ms*(i+1) 스텝 스트리밍, replay는 즉시 전체 emit) + `src/lib/useRunEngine.ts`(React 훅 래퍼). `src/features/run/`: `StepTimeline`(guardrail만 경고 톤 구분) + `RunScreen`(5상태 프레젠테이션, 스트리밍 미완료 시 승인 버튼 disabled) + `RunPage`(컨테이너 — `/case/:caseId/approve`·`/run/:runId` 두 라우트를 하나로 공유). 기존 no-op였던 `CommandBar` 제출(→ command 데모 런)과 `ApprovalCard` 프로액티브 행 클릭(→ preparedRunRef 재생)을 실제 네비게이션으로 배선. 최종 전체 리뷰(opus)에서 Critical/Important 0건, Minor 2건 중 1건(RunPage 레벨 스트리밍-disabled 통합 테스트 부재)만 수정 — 픽스 서브에이전트가 fake timer 아래 `findByRole`(waitFor 기반, 실시간 폴링 필요)을 써서 타임아웃 나는 걸 컨트롤러가 직접 `getByRole`(버튼은 스트리밍 여부와 무관하게 항상 동기 렌더됨)로 교체해 해결.
- 남은 일 / 중단 지점: 없음. approvalStore.decide() 등 승인 결정 영속화·caseStore 상태 전이는 명시적으로 1.6(M3~M5 루프) 몫으로 남김 — 지금 `RunPage.onApprove`는 `/done`으로 이동만 한다. `RunViewState.default.mode` 필드는 RunScreen이 아직 안 읽음(1.6에서 command/replay UI 차이가 더 생기면 쓰일 수 있음, 지금은 무해한 미사용 필드로 남김 — 최종 리뷰 Minor, 고치지 않기로 함). command 모드는 자연어 파싱 없이 항상 고정 데모 런(#4790)으로 매핑(실 파싱은 백엔드 단계). 다음은 ROADMAP 1.6(M3 초안 + M4 승인 + M5 완료 + 상태 전파, E2E) — L2.
- 결정 사항:
  - ARCHITECTURE.md의 "M4는 이 화면의 mode='pre_approval' 특수 케이스" 문구는 별도 모드 값이 아니라 "M4 라우트가 이 화면(mode='approval')의 특수 사용처"로 해석 확정(브레인스토밍 질문으로 사용자 확인) — `RunConfig.mode`는 3값(`command`/`approval`/`replay`) 그대로.
  - M4(`/case/:caseId/approve`)와 M9(`/run/:runId`) 라우트가 동일한 `RunPage` 컴포넌트를 공유(브레인스토밍 질문으로 확정) — `caseId` 파라미터면 `caseId+mode==='approval'`로, `runId` 파라미터면 `runKey`로 `RUN_CONFIGS`를 조회.
  - 런은 전역 zustand 스토어를 만들지 않음 — 화면 하나가 소유하는 로컬 상태(useRunEngine의 useState)로 충분하다고 판단(caseStore/approvalStore와 달리 여러 화면이 동시 구독할 필요가 없음).
- verify 상태: PASS (typecheck 0, lint 0, test 35 files/183 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2에 `src/features/run/` 추가, §5 런 시스템에 "구현(1.5)" 문단 추가(executeRun/useRunEngine/RunPage 공유 사실 + approvalStore 연동은 1.6 몫 명시).

---

### [2026-07-06] 1.4 — 완료
- 한 일: `/case/:caseId`가 실제 M2 케이스 시트를 렌더. `src/components/BottomSheet.tsx`(공용 모달 프리미티브 — scrim/slide-up/dismissible/footer, 도메인 타입 모름). `src/features/case/CaseSheet.tsx`(1단계 §M2 5블록 고정: 요약/AI확인내용/서류체크리스트/근거/에이전트활동 + ActionBar 2개 — citation 0건이면 근거 경고 + **승인이 필요한 액션만** locked, 5개 케이스 전부 이 컴포넌트 하나로 커버·분기 없음). `src/features/case/CaseSheetPage.tsx`(`<BriefingHomePage/>`를 배경으로, `<CaseSheet/>`를 오버레이로 구성 — 2단계 딥링크맵의 "M1 위에 오버레이" 요구를 진짜 background-location 대신 M1 렌더러 재사용으로 근사). 어드버서리얼 리뷰에서 Important 1건(`activity`가 비어 있으면(mohammad/hiring) `nextWake`까지 통째로 안 뜨던 버그) 발견 후 수정.
- 남은 일 / 중단 지점: 없음. 진짜 background-location(M7 생기면 재검토), half↔full 드래그 제스처, M9 재생 뷰 연결, tranCase 확인완료 후 UI 반영은 계획 문서에 범위 밖으로 명시. Minor로 남긴 것(고치지 않음, 문제 아님): `BriefingHomePage`와 `CaseSheetPage`가 caseStore 시딩 `useEffect`를 각자 갖고 있어 중복이지만 React 마운트 순서상 안전(자식이 먼저 시드하고 부모는 가드에 걸려 스킵) — 다음에 손댈 사람은 공유 훅으로 뽑을지 고려. 존재하지 않는 caseId로 이동하면 안내 없이 조용히 M1만 보임(M7·실제 딥링크 검증 붙을 때 재검토). 다음은 ROADMAP 1.5(런 엔진, **L3** 협업 태스크 — v3의 renderRun() 각본 재생 로직 이식) 또는 2.1(M7 케이스 목록) — ROADMAP 순서상 1.5가 다음이지만 L3라 더 무거운 협의가 필요.
- 결정 사항:
  - citation 등급(A/B/C/E) 배지는 기존 `Badge` 컴포넌트를 재사용하지 않고 새 인라인 span으로 렌더 — 프로토타입 v3 `.cite .g`(18×18 정사각형)가 `Badge`의 알약형과 시각이 달라 억지로 끼워맞추지 않음(`size-[18px]`는 1.3의 `size-[22px]`와 같은 성격의 알려진 국지적 예외).
  - citation-잠금은 `card.primaryAction.requiresApproval`이 true인 액션에만 걸린다 — tranCase처럼 승인이 필요 없는 primaryAction(kind:'confirm')은 citation 0건이어도 잠기지 않는다(GOTCHAS §2가 말하는 건 "승인 게이트"지 "모든 액션 차단"이 아님).
- verify 상태: PASS (typecheck 0, lint 0, test 30 files/162 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/case/` 사례 추가.

---

### [2026-07-06] 1.3 — 완료
- 한 일: M1 오늘 브리핑 홈을 5상태 전부 구현하고 `/` 라우트에 연결(더 이상 PlaceholderScreen 아님). `src/types.ts`에 `NextActionKind`(approve/draft/detail/thread/package/confirm) 추가 + `src/mocks/fixtures.ts` CASE_CARDS 10개 액션에 kind 채움. `src/lib/actionNav.ts`(`useNextAction()` — kind→이동/인라인 액션, confirm은 risk_review→completed가 CASE_TRANSITIONS에 없어 이동 없이 evidence만 남김). `src/lib/briefing.ts`(`greetingText`/`sortCards`/`visibleCardsForRole`/`recommendReason` 순수 함수). `src/components/icons.tsx`에 IconSpark/IconWait 추가. `src/features/briefing/`: `BriefingHeader`/`SummaryStatRow`/`CommandBar`(작은 프레젠테이션), `ApprovalCard`(hero/compact, 배지 순서 고정, CTA 2개), `BriefingScreen`(5상태 전부 담은 순수 프레젠테이션 — 이번 마일스톤 DoD), `BriefingHomePage`(caseStore 시딩 + role/greeting 계산하는 컨테이너). 어드버서리얼 리뷰에서 Important 3건 발견 후 수정: (1) compact 카드도 primary(파랑) CTA를 렌더해 "화면당 파랑 1개" 위반 — compact는 secondary variant로 교정 (2) hero 추천 이유가 dead ternary로 항상 undefined — `recommendReason()` 헬퍼로 실연결 (3) `greetingText`가 테스트만 되고 실제 화면은 호칭 없이 인사문을 재구현 — `BriefingViewState`에 `greeting` 필드 추가해 실연결.
- 남은 일 / 중단 지점: 없음. 컨테이너/프레젠테이션 분리 패턴(`<Name>Screen` + `<Name>Page`)이 확립됐으니 M2~M9도 따르길 권장. role(manager 고정, 4.2 몫)·근로자수(5 고정, 3단계 몫)·실제 fetch/오프라인 감지(백엔드 접속점 이후)·Toast(스펙 갭)·CommandBar→M9 연결(1.5)·프로액티브 행→런 재생 뷰(1.5)는 계획 문서에 범위 밖으로 명시. 다음은 ROADMAP 1.4(BottomSheet + M2 케이스 시트) — L2.
- 결정 사항:
  - 실행 중 세션 사용량 한도로 워크플로우가 한 번 중단됐다(9:50pm 리셋) — task3(briefing.ts)는 이미 완성돼 있었지만 커밋 전에 끊겨 수동으로 확인 후 커밋, 나머지(4/6/7/8)는 순차 Agent 디스패치로 이어서 진행. 최종 결과물이나 커밋 이력에는 영향 없음.
  - `ApprovalCard`의 오프라인 처리는 계획 원안(카드 전체 fieldset 잠금)에서 `offlineDisabled` prop 방식으로 구현 중 조정됨 — `requiresApproval:true`인 CTA만 잠그고 읽기 액션(예: 초안 보기)은 오프라인에서도 유지(GOTCHAS §3 "초안 보기 등 읽기 액션은 캐시 범위 내 허용"과 정확히 부합, 원안보다 개선).
  - `router.test.tsx`의 잘못된 caseId 리다이렉트 테스트가 기대하는 텍스트를 `/M1 오늘 브리핑/`(옛 PlaceholderScreen 문구)에서 `/화성 1공장/`(BriefingHomePage 헤더 회사명)로 갱신 — index route 교체의 자연스러운 결과.
- verify 상태: PASS (typecheck 0, lint 0, test 27 files/148 tests passed, build OK). `router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 flake하는 기존 이슈(1.1부터)는 이번 세션에서는 재현되지 않았다.
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/briefing/`을 컨테이너/프레젠테이션 분리 패턴의 실제 사례로 추가.

---

### [2026-07-06] 1.2 — 완료
- 한 일: 공용 컴포넌트 6종 + 배지 색 규칙 매핑 모듈. `src/components/Badge.tsx`(tone 7종: critical/warning/pending/info/success/neutral/line, 프로토타입 v3 `.bdg` 그대로), `Button.tsx`(variant 3종 primary/secondary/outline + size default/sm, 네이티브 button 속성 pass-through), `Card.tsx`(variant default/hero + interactive, margin은 컴포넌트에 강제 안 함), `SafetyNotice.tsx`(props 없음 — GOTCHAS §3 고정 문구를 타입으로 강제), `OfflineBanner.tsx`(v3에 시각 참고 없어 스펙 텍스트만으로 신규 설계), `Skeleton.tsx`(bg-hairline pulse, motion-reduce 대응). `src/lib/badgeTone.ts` — `severityTone`/`approvalStatusTone`/`caseStateTone`(1단계 §0.2 표 → BadgeTone 매핑, Badge는 이 파일에서 타입만 import해 도메인 타입 격리 유지). `icons.tsx`에 `IconShield` 추가(기존 4개 아이콘 불변). `tokens.css`/`tailwind.config.js`에 이번 태스크에 필요한 토큰 전부 등록(배지 배경 틴트 4색 + 텍스트 오버라이드 2개, 배지 radius 8px, surface-press, 버튼 치수 5개, SafetyNotice 치수 2개) — 임의값 Tailwind 클래스 0건.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 1.3(M1 브리핑 홈, 5상태 전부) — 이번에 만든 6개 컴포넌트 + badgeTone이 그 화면의 기반이 됨. L2라 계획 승인 대상.
- 결정 사항:
  - 배지 radius는 rules/design.md 요약(칩·배지 14)과 달리 실제 8px(`--r-badge`) — 프로토타입 v3 `.bdg{border-radius:8px}`가 시각 기준(rules/design.md 자체 원칙)이라 프로토타입을 따름. rules/design.md 요약 문구 자체는 이번 태스크 범위 밖이라 고치지 않음(다음에 손대는 사람이 "14로 되돌리는" 실수를 하지 않도록 여기 기록).
  - Button/Card는 레이아웃(margin/flex:1)을 자체에 강제하지 않음 — 프로토타입 정적 HTML과 달리 재사용 컴포넌트라 간격은 호출부(부모 레이아웃) 책임으로 뺌.
  - 배지 텍스트 색은 종류별로 기본 토큰과 다른 값 사용(critical: 아이콘/닷 등에 쓰는 #EF4444가 아니라 배지 전용 #DC2626, warning도 마찬가지) — 프로토타입 원본 그대로, `critical-text`/`warning-text`로 별도 등록.
  - `src/router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 실패(단독 실행 시엔 항상 통과) — 이번 태스크가 만든 파일과 무관(router.tsx/Shell.tsx 무변경 확인됨), 1.1부터 있던 타이밍 이슈로 추정. 다음에 이 테스트를 만지는 사람은 참고.
- verify 상태: PASS (typecheck 0, lint 0, test 19 files/104 tests passed, build OK). router.test.tsx 간헐적 flake는 위 참고.
- 지도/규칙 갱신: 없음(ARCHITECTURE.md의 "화면 컴포넌트" 항목은 아직 `src/features/`를 가리키는데, 이번 6개는 도메인 화면이 아니라 공용 프리미티브라 `src/components/`에 그대로 있음 — 별도 갱신 불필요 판단).

---

### [2026-07-06] 1.1 — 완료
- 한 일: ROADMAP 1.1(라우터+딥링크 맵+Shell) 전체 9태스크 완료. `src/lib/routes.ts`(`ROUTES`/`ROUTE_PATHS` 딥링크 경로 단일 출처), `src/lib/cn.ts`(legacy `features/pc/ui.tsx`에서 이식), `src/components/icons.tsx`(탭 아이콘 4종, `prototype_v3.html`에서 이식), `src/screens/PlaceholderScreen.tsx`(미구현 라우트 공용 자리표시자), `src/lib/deeplink.ts`(`validateIdParam` — zod 기반 loader 팩토리, `zod` 신규 의존성 4.4.3), `src/lib/nav.ts`(`useNav()` — 명명된 내비게이션 메서드 12개, 전부 `ROUTES.*` 위임), `src/Shell.tsx`(레이아웃 라우트 — <1024px 모바일 탭바/이상 PC 헤더 분기 + `useDeepLinkBackstack()` 훅, 콜드 스타트 시 히스토리를 [M1, 목적지]로 재작성), `src/router.tsx`(자식 라우트 12개로 전체 라우트 트리 완성, 그중 6개는 `validateIdParam` 기반 loader 보유). M0.1 자리표시자였던 `src/App.tsx`/`src/App.test.tsx`는 삭제(Shell로 완전 대체). 두 DoD(라우트 스냅샷 테스트, 딥링크 백스택=M1→목적지)를 `src/router.test.tsx`의 실제(비모킹) 라우터 테스트로 검증.
- 남은 일 / 중단 지점: 없음. 1.2/1.3/1.4/2.1이 의존하는 라우팅·딥링크·Shell·nav 인프라는 모두 준비 완료.
- 결정 사항:
  - `/case/:caseId`(bare, M2 케이스 바텀시트)와 `/onboarding/workers`(O1 근로자 등록)를 라우트 트리에 추가 — `ARCHITECTURE.md` 원래 라우트 표에는 없었지만 2단계 딥링크맵 스펙(N03 등은 `case/{id}`로, N21은 `onboarding/workers`로 직결)이 요구해 반영. 같은 세션에서 ARCHITECTURE.md §3 표도 갱신.
  - 계획 외 보정: 태스크 도중 `router.navigate(-1)`이 당시 vitest 3.2.6에서 throw(vitest-dev/vitest#8374 — Node 24 아래 jsdom AbortSignal 브랜드 체크 버그)하는 것을 발견. 사용자 확인 후 근본 해결을 택해 `vitest` `^3.0.0` → `^4.1.10` 업그레이드. 테스트 완화 없이 버그 자체를 제거, 이후 전체 스위트 통과.
  - 알려진 사소한 갭(차단 아님, 향후 세션 참고용): (1) `Shell.tsx`의 탭바 치수(`h-[62px]`/`text-[11px]`/`pb-[62px]`)는 탭별기획 §0.2가 지정한 정확한 값이지만 아직 `tokens.css`/`tailwind.config.js`에 이름 있는 토큰으로 등록되지 않음 — 향후 디자인 토큰 패스에서 정리 가능. (2) 라우트 스냅샷 테스트는 `path`/`hasLoader`/`children` 형태만 검사해 loader가 엉뚱한 라우트에 붙는 경우(예: `case` 라우트에 `runId` validator)는 단독으로 못 잡음 — 딥링크 백스택 테스트 2개가 부분적으로만 보완. (3) 스코프 의도적 제외(완료 아님, 착오 방지용 명시): M2 오버레이 실제 렌더링(1.4), TabBar 미확인 배지(스토어 연결 후), `filter` 쿼리 파라미터 값 검증(2.1), 딥링크 검증 실패 시 토스트 문구(Toast 컴포넌트 자체가 아직 없음 — 담당 태스크 불명확한 스펙 갭).
  - 최종 whole-branch 리뷰 반영: (1)은 이 패스에서 이미 토큰화 완료(`--tabbar-h`/`--tabbar-label-fs` + `spacing.tabbar`/`fontSize.tabbar-label`)로 해소됨. 추가로, `useDeepLinkBackstack`의 콜드 스타트 `navigate(target)` 호출(`/case/:caseId` 등)이 현재 location `state`를 싣지 않는다는 점이 발견됨 — 1.4가 M2 바텀시트를 "background location" 오버레이 패턴(시트 라우트에 배경 위치를 state로 주입)으로 구현할 때 이 훅과 조율이 필요하니 1.4 착수 시 다시 조사하지 않도록 여기 남긴다.
- verify 상태: PASS (typecheck 0, lint 0, test 12 files/57 passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` 진입점 표(라우팅·딥링크→`src/router.tsx`, 화면 셸→`src/Shell.tsx`)와 §3 라우트 표(`/case/:caseId` bare, `/onboarding/workers` 추가) 갱신.

---

### [2026-07-06] 0.5 — 완료
- 한 일: `reference/prototype_v3.html`·`reference/specs/*`(12_모바일퍼스트_재설계 사본, 기존 세션에서 이미 복사되어 diff 확인만 함)을 출처로 `src/mocks/` 4파일 이식. `fixtures.ts` — v3 CASE 레지스트리 5건(nguyen/bayar/mohammad/tranCase/hiring)을 `CaseCard[]`(§0.4)로, M2 시트용 데이터(kv·docs·citations·activity·nextWake)를 로컬 `CaseSheet` 타입으로 정규화. severity/그룹은 v3 `caseRows()`의 sev 필드(warn/crit/info/neut)로 근거를 삼아 매핑. `drafts.ts` — DRAFT 3건(nguyen/mohammad/tranReminder), KR+VN(nguyen,tranReminder)/KR+EN(mohammad) — SPEC_INDEX가 요구한 EN 포함. `runs.ts` — APPROVE 6건(nguyen/candidate/bayarPkg/mohammad/hiring/tranReminder)을 `RunConfig`/`RunStep`으로. `evidence.ts` — 초기 EV 시드 5건만(런타임 addEv 이후 항목은 향후 evidenceStore.append 몫). `src/types.ts`의 `EvidenceEvent`에 표시용 옵션 필드 3개(`summary`/`actor`/`evidenceRef`) 추가(M8 EventTimelineItem 이식, 기존 필드는 불변이라 M0.4 테스트 영향 없음).
- 남은 일 / 중단 지점: 없음. PKG(candidate/hiring 패키지 본문)·command/replay 런(#4790/#4796 draft/#4788 replay)·M7 목록 그룹핑(g 필드)은 의도적으로 제외 — 각각 M2.4·M1.5(L3)·2.1 태스크 몫. bayar는 v3 시트에 CTA가 1개뿐이라 secondaryAction('상세 보기')을 새로 만들어 채움 — M1.4에서 실제 UI 확정 시 재검토. 다음은 ROADMAP 1.1 (라우터+딥링크 맵, Shell). L2라 계획 승인 대상.
- 결정 사항:
  - Case.state 매핑(추론, v3에 명시 없음): nguyen·mohammad=approval_pending / bayar=blocked(GOTCHAS "high risk→blocked") / tranCase=risk_review / hiring=draft.
  - RunStep에 공식 5종(thinking/tool_call/guardrail/handoff/replan, GLOSSARY) 밖의 'wait'를 로컬 확장으로 추가 — v3의 "승인 대기" 스텝을 표현하려는 것으로, M9 RunStep으로 승격 시 스펙에 먼저 반영 필요.
  - CaseDocStatus는 M2 스펙의 4값(missing/requested/received/company_check) 밖에 'expiring'·'pending' 2개를 fixtures.ts 로컬 타입에 추가 — v3 라벨(만료 예정/대기)을 손실 없이 옮기기 위함.
  - EvidenceEvent 확장 필드는 모두 optional이라 evidenceStore/guardrails.test.ts 기존 계약 불변. cat(위험감지/초안생성/승인/전달) 필터 그룹은 저장하지 않고 추후 selector로 파생 예정(2.3).
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed — 신규 mocks는 순수 데이터라 별도 테스트 없음, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md`의 mock 데이터 진입점 행을 4파일 구조로 갱신.

---

### [2026-07-06] 0.4 — 완료
- 한 일: zustand 스토어 3종 — `src/stores/caseStore.ts`(GOTCHAS §2 상태머신 `transition` 검증), `approvalStore.ts`(`requestApproval`/`decide`/`dispatch`, idempotencyKey 중복 차단, 승인 없이 dispatch throw), `evidenceStore.ts`(append-only, 이벤트 Object.freeze). `src/lib/guardrail.ts`에 `GuardrailError`. `src/types.ts`에 `Approval`·`EvidenceEvent`(+ EvidenceType) 추가. 가드레일 테스트 `src/stores/guardrails.test.ts` 12개.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.5 (mocks 이식 — v3 CASE/DRAFT/APPROVE/EV → fixtures, 스펙: docs/SPEC_INDEX.md 이식표, DoD: typecheck 통과 + PII 원문 없음). L1.
- 결정 사항:
  - 3개 가드레일 테스트: (1) 승인 없이 dispatch 불가 (2) evidence append-only(수정·삭제 액션 부재 + 동결) (3) 중복 승인 차단(같은 key no-op) — 전부 통과. Case 상태 전이 보강 3개 추가.
  - 직접 발송 함수 미구현. dispatch는 approved에서만 mock 경계까지(`{dispatched:true}`), 실제 발송 없음.
  - EvidenceEvent에 원문/PII 필드 없음 — hash만 허용.
  - 스토어 경로 = `src/stores/`. 아직 App에 미연결(M1.x에서 연결) — 빌드 번들에는 미포함.
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.3 — 완료
- 한 일: `src/types.ts`에 §0.4 공용 타입 이식(Severity/CaseState/Role/ApprovalStatus/NextActionRef/WorkerRef/CaseCard/Citation). `src/lib/dday.ts`에 `calcDday(target, base)`(UTC 자정 정규화, 'YYYY-MM-DD'·'YYYY.MM.DD'·Date 입력) + `dDayLabel` + `dDayTone`(배지 색 규칙). `src/lib/mask.ts`에 `maskId`(영숫자→*, 구분자 유지). 단위 테스트 2파일(22 tests).
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.4 (스토어 3종 case/approval/evidence + 가드레일 테스트, 스펙: docs/GOTCHAS §1·2 — 아직 `docs/GOTCHAS.md`가 이 루트에 있는지 확인 필요, 없으면 `외고반장_통합/13_클로드코드_구현패키지/docs/GOTCHAS.md` 참조). L2라 계획 승인 대상.
- 결정 사항:
  - dDay 부호 규칙: 양수=남은 일수(D-N), 0=D-day, 음수=경과(D+N). tone은 토큰 색 이름(critical/warning/info/neutral)으로 반환 — 배지가 tokens와 1:1.
  - `calcDday`는 UTC 자정 기준으로 계산해 로컬 타임존·DST와 무관하게 결정적. 테스트는 기준일 주입.
  - `maskId`는 원문 digit 미보존(전체 마스킹) — safety.md "원문 금지" + 3단계 "화면에는 ***-*******만" 준수.
- verify 상태: PASS (typecheck 0, lint 0, test 22 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.2 — 완료
- 한 일: `src/styles/tokens.css`에 prototype_v3 `:root` 토큰 그대로 이식(reduced-motion 오버라이드 포함). `tailwind.config.js` theme를 토큰 `var()`에 연동(colors/radius/shadow/duration/timing + fontFamily). `src/index.css`에서 tokens + Pretendard(가변폰트 dynamic-subset) import, base layer에 `bg-canvas/text-ink/font-sans` 적용. 토큰 스냅샷 테스트 1개(`src/styles/tokens.test.ts`) — 기준 `:root` 블록만 파싱, 빈 맵 가드 포함.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.3 (`src/types.ts` + `calcDday`·`maskId` 유틸 + 단위 테스트, 스펙: reference/specs 1단계 §0.4).
- 결정 사항:
  - Pretendard는 정적 dynamic-subset(9웨이트 전부 → CSS 526kB) 대신 **가변폰트 dynamic-subset** 사용 → CSS 53.8kB. family `Pretendard Variable` 우선, `Pretendard` 폴백.
  - 토큰 단일 출처 = tokens.css. tailwind은 var() 참조만. duration도 var()라 reduced-motion 캐스케이드 유지.
  - 스냅샷 테스트는 처음에 `?raw` 임포트가 vitest에서 빈 문자열 → 거짓 통과(`{}`) 발생 → cwd 상대경로 fs 읽기 + 개수 가드로 교정.
- verify 상태: PASS (typecheck 0, lint 0, test 2 passed, build OK, CSS 53.8kB).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.1 — 완료
- 한 일: 루트에 Vite6+React19+TS5.7+Tailwind3.4+react-router-dom7+zustand5 스캐폴드. `npm run verify`(typecheck→lint→test:run→build) 구성. 빈 셸(`src/App.tsx` = `외고반장` h1) + 라우터(`src/router.tsx`) + 렌더 테스트 1개(`src/App.test.tsx`). ESLint flat config는 앱 트리(root `src`)만 대상 — legacy/외고반장_통합 등 비앱 트리는 ignore.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.2 (tokens.css + tailwind theme, v3 `:root` 이식).
- 결정 사항:
  - 프로젝트 레퍼런스(tsconfig.node.json) 제거 → 단일 tsconfig(`src` + `vite.config.ts`), `@types/node` 추가. `tsc -b` composite 충돌 회피.
  - vitest는 v3 사용(v2.1은 vite6와 nested-vite 타입 충돌). `defineConfig`는 `vitest/config`에서 import.
  - 스토어/토큰/mocks는 범위 밖이라 미포함(0.2·0.4·0.5).
- verify 상태: PASS (typecheck 0, lint 0, test 1 passed, build OK). dev 서버 부팅 확인(localhost:5173).
- 지도/규칙 갱신: 없음.

---

(아직 기록 없음 — M0.1부터 시작)
