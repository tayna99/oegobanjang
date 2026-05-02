# API Contract

## 1. 목적

이 문서는 frontend와 backend 사이의 API 계약을 정의한다.

---

## 2. 공통 응답 형식

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

에러 예시:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청값이 올바르지 않습니다."
  }
}
```

---

## 3. Health API

```txt
GET /api/v1/health
```

응답:

```json
{
  "status": "ok"
}
```

---

## 4. Agent 실행 API

```txt
POST /api/v1/agent/run
```

요청:

```json
{
  "request_id": "req_001",
  "user_id": "user_001",
  "company_id": "company_001",
  "user_message": "베트남 E-9 근로자 3명 추가 채용 준비해줘. Nguyen 체류만료도 확인해줘."
}
```

응답:

```json
{
  "request_id": "req_001",
  "detected_intents": ["HIRING", "VISA_CHECK"],
  "plan": {
    "steps": [],
    "required_agents": [],
    "requires_approval": true
  },
  "agent_results": [],
  "approval": {
    "required": true,
    "status": "PENDING",
    "reason": "외부 발송 또는 전문가 전달 전 담당자 승인이 필요합니다."
  },
  "evidence_events": [],
  "final_response": "요청을 분석하고 실행 계획 초안을 생성했습니다."
}
```

---

## 5. 주요 API 목록

```txt
/api/v1/auth
/api/v1/companies
/api/v1/workers
/api/v1/hiring
/api/v1/visas
/api/v1/documents
/api/v1/contacts
/api/v1/approvals
/api/v1/evidence
/api/v1/agent
```

---

## 6. 승인 API

```txt
POST /api/v1/approvals/{approval_id}/approve
POST /api/v1/approvals/{approval_id}/reject
```

승인 필요한 작업은 Agent가 직접 실행하지 않고 approval pending 상태로 넘긴다.

---

## 7. Evidence API

```txt
GET /api/v1/evidence?request_id={request_id}
```

요청 단위 Evidence Log를 조회한다.