## 작업 내용

- 

## 관련 태스크

- [ ] `plans/ROADMAP.md` 태스크: (예: R0.2)
- [ ] (legacy 백엔드/Agent Runtime 작업인 경우) `legacy/missions/active/`:

## 변경 파일

- 

## 검증 결과

- [ ] `npm run verify` 통과 (typecheck → lint → test → build)
- [ ] (`backend/` 변경 시) `cd backend && uv run pytest` 통과
- [ ] (`db/` 변경 시) `db/validate.py` 통과
- [ ] (legacy `backend/`/Agent Runtime 변경 시) `legacy/scripts/verify_all.sh` 등 legacy 검증 통과 + eval case 추가/확인
- [ ] Evidence Log 생성 확인

## 안전성 체크

- [ ] 비자 가능 여부를 확정하지 않음
- [ ] 법률·노무 자문을 하지 않음
- [ ] 정부 포털 제출 자동화 없음
- [ ] 외부 메시지 자동 발송 없음
- [ ] 행정사/노무사 패키지 자동 전송 없음
- [ ] 근로자 감시/이탈 예측 없음
- [ ] 후보자 성실도/국적별 선호 판단 없음
- [ ] 승인 필요한 작업은 `approval_required=true` 처리
- [ ] 민감정보 원문 로그 저장 없음

## 문서 영향

- [ ] `db/schema.sql` 변경 시 `docs/DB_SCHEMA.md` 동기화
- [ ] `backend/app/api/` 변경 시 `backend/README.md` 수정
- [ ] 화면/스펙 변경 시 `docs/SPEC_INDEX.md`·`docs/ARCHITECTURE.md` 갱신
- [ ] (legacy Agent Runtime/RAG 변경 시) `legacy/docs/AI_OS_DESIGN.md`·`TOOL_CONTRACT.md`·`RAG_STRATEGY.md` 수정

## 남은 리스크

- 

## 실행 로그

```txt
여기에 테스트/eval 실행 결과를 붙여넣기
```
