# LangChain 1.0 Day-1 Design — Section Rationale Deep Dive

> 작성일: 2026-05-09
> 목적: `langchain-1-ideal-day1-design.md`의 각 섹션이 **왜 그렇게 설계됐는지** 깊이 있게 설명. 코드 패턴 자체가 아니라 그 패턴이 막는 사고와 만드는 안전 invariant를 다룸.
> 사용법: reference design의 각 섹션을 구현하기 전에 이 문서로 의도를 먼저 이해. PR description에 직접 인용 가능.

---

## §0. RuntimeMode enum — 왜 만들었나

### 5가지 이유

#### 1. 외부 API 호출을 명시적으로 켜는 스위치

LLM 호출은 돈이 들고, 네트워크가 필요하고, 응답이 매번 달라진다. 코드 곳곳에서 자동으로 호출되면 곤란하다.

```python
if state.runtime_mode == RuntimeMode.LANGCHAIN_JUDGMENT:
    chain = WorkforceJudgmentChain()  # ← 여기서만 OpenAI 호출
    response = chain.invoke(...)
```

`runtime_mode`가 없으면 "어디서 LLM이 호출되는지" 코드 검토만으로 안 보임. enum 하나로 **호출 진입점이 명시화**됨.

#### 2. CI / 테스트 환경에서 사고 방지

```python
DETERMINISTIC = "deterministic"   # default — API key 없어도 돌아감
LANGCHAIN_JUDGMENT = "langchain_judgment"  # explicit — API key 있어야 함
```

CI나 동료의 로컬 환경에는 `OPENAI_API_KEY`가 없을 수 있다. default가 `DETERMINISTIC`이면 **API key 없는 환경에서도 모든 테스트가 돌아간다**. 만약 default가 langchain이었다면, 누군가의 PR 테스트가 "API key 없음"으로 실패하거나, 더 나쁘게는 **실수로 운영 키로 테스트가 돌면서 비용이 발생**할 수 있다.

#### 3. 운영 사고 격리 — feature flag 역할

LLM 호출은 잠재적 사고 지점이다 (응답 형식 변형, 비용 폭증, latency 급증, 가드레일 우회). `runtime_mode`가 있으면 사고 시 한 줄로 전체 LLM 호출을 끌 수 있다:

```python
if EMERGENCY_DISABLE_LLM:
    state.runtime_mode = RuntimeMode.DETERMINISTIC
```

이게 **kill switch**다. enum이 없으면 끄려고 코드 수정 + 배포가 필요.

#### 4. A/B 테스트 / 점진 롤아웃

같은 사용자 요청을 두 모드로 처리해서 비교 가능:

```python
state.runtime_mode = (
    RuntimeMode.LANGCHAIN_JUDGMENT
    if random() < 0.05
    else RuntimeMode.DETERMINISTIC
)
```

deterministic 결과와 LLM 결과가 얼마나 다른지 evidence_log에서 비교 가능. 점진 롤아웃의 기본 인프라.

#### 5. enum vs bool — 왜 bool이 아닌가

```python
# bool로 했다면:
use_llm: bool                # 처음
use_langchain: bool          # 추가
use_anthropic: bool          # 또 추가  ← 조합 폭발
```

bool 4개면 16가지 조합 중 의미 있는 건 4가지뿐. enum이면 **한 번에 하나만 선택**되도록 강제. JSON 직렬화도 깔끔(`"runtime_mode": "deterministic"`).

### `default()` classmethod의 의도

```python
@classmethod
def default(cls) -> "RuntimeMode":
    return cls.DETERMINISTIC

# Pydantic 모델에서:
runtime_mode: RuntimeMode = Field(default_factory=RuntimeMode.default)
```

`default_factory=RuntimeMode.default`가 `default=RuntimeMode.DETERMINISTIC`보다 좋은 이유:

- "default가 어디 정의됐는지" 한 곳(`RuntimeMode.default()`)만 보면 됨
- 나중에 default를 바꿀 때 enum 안에서만 수정 (사용처 100군데 안 고쳐도 됨)
- 테스트에서 `RuntimeMode.default()`를 명시적으로 부를 수 있음

### ⚠ 현재 결정과의 긴장

현재 migration plan이 `create_agent`-first로 변경되면서 `runtime_mode`의 위상이 약해질 수 있다:

| | day-1 reference | 현재 create_agent-first |
|---|---|---|
| `runtime_mode`의 의미 | LangGraph만 vs LangGraph+LLM | 테스트 격리용으로만 |
| Default | DETERMINISTIC (안전) | LLM 호출이 정상 경로 |
| Kill switch | 강한 가치 | circuit breaker 같은 다른 메커니즘이 더 적합 |

이 reference 문서의 다른 패턴들(`BaseStructuredChain`, validator 분리)은 더 보편적으로 가져갈 자산이고, `runtime_mode`는 운영 정책에 따라 빼도 되는 옵션이다.

---

## §3. IntentClassification schema — 5가지 핵심 포인트

### 1. ⭐⭐⭐ Schema = LLM과 Python의 공통 계약

```
                  IntentClassification (Pydantic)
                         /              \
            ┌───────────▼─────┐    ┌──────▼──────────┐
            │ JSON Schema     │    │ Python 타입      │
            │ (LLM에게 전달)   │    │ (코드에서 사용)   │
            └─────────────────┘    └─────────────────┘
                  ↓                          ↑
            LLM이 이 형식대로            Pydantic이 검증해서
            JSON 생성 강제              IntentClassification 인스턴스 반환
```

"LLM이 만드는 것"과 "Python이 읽는 것"이 같은 정의에서 나옴. 양쪽이 어긋날 수 없음.

### 2. ⭐⭐ `list[Intent]` — enum이라 LLM이 못 어김

`Intent`는 도메인 enum 8개 고정. `list[Intent]`로 타입 박으면:
- LLM이 `"hiring"`(소문자)이나 `"hire"` 같은 변형 못 씀
- 새로운 intent 발명 못 함 (`"NEW_HIRING_REQUEST"` 같은)
- 어기면 LangChain `with_structured_output`이 자동 재시도 (`max_retries=2`)
- 재시도 후 실패 → ValidationError로 명시적 노출

**현재 코드**: `[Intent(i) for i in parsed.get("intents", []) if i in _SUPPORTED_INTENTS]` (3겹 방어)
**Day-1 1.0**: `result.intents` (이미 list[Intent], 검증 끝)

### 3. ⭐⭐ `description=...`이 LLM에게 전달되는 instruction

```python
intents: list[Intent] = Field(
    default_factory=list,
    description="감지된 intent. UNSUPPORTED_*는 차단 사유.",  # ← LLM이 봄
)
```

`with_structured_output`이 description을 JSON Schema로 변환해 LLM에 전달. **prompt에 안 써도 LLM이 알게 됨.** prompt 길이 줄고, 의미가 schema 한 곳에 모임.

`rationale: str` 필드도 같은 메커니즘으로 "왜 그렇게 분류했는지 한 줄 적어"가 자동 지시됨.

### 4. ⭐ `default_factory=list` — empty intents의 의미

빈 리스트가 valid한 응답:
- LLM이 분류 못 하겠다 → 빈 리스트
- 빈 리스트 = "분류 실패" 명시적 신호
- planner가 "intents 비었으면 unsupported" 분기 가능
- LLM이 억지로 아무 intent나 고르는 hallucination 방지

### 5. ⭐ `rationale` — 무료 디버깅 정보

```python
rationale: str = Field(default="", description="분류 근거 한 줄. 디버깅 용도.")
```

이 한 줄로 얻는 것:
- LLM이 왜 그 intent를 골랐는지 evidence_log에 남음
- 운영 사고 시 디버깅 가능
- prompt에 "이유도 적어줘" 같은 추가 명령 불필요

### 진짜 포인트

**"LLM 응답 형식을 prompt 텍스트로 설명하지 말고 타입으로 강제하라"**가 LangChain 1.0의 핵심 철학. Pydantic 클래스 한 번 정의하면 schema 자동 전달 + 형식 어기면 자동 재시도 + 검증된 객체 반환 + description으로 추가 instruction까지.

**이 한 클래스가 prompt 30줄 + parser 20줄 + validator 15줄을 대체.**

---

## §4. workforce schema — 7가지 핵심 패턴

### 1. ⭐ `Literal[...]` 천지 — 토큰 레벨 강제

```python
status: Literal["draft_ready", "needs_more_input", "needs_human_review", "blocked"]
```

`Literal`은 JSON Schema의 `enum` 제약으로 변환. **OpenAI Structured Outputs (`strict=True`)에서 token-level grammar에 박혀** LLM이 변형 생성을 물리적으로 못 함.

이 schema에서 `Literal`이 박힌 곳: readiness_status(5), target(3), risk_type(4), level(3), evidence_grade(6), intent(5), status(4), agent(고정).

### 2. ⭐⭐ `blocked_actions: list[Literal[...]]` — 이중 제약

리스트인 동시에 각 원소도 enum. AGENTS.md의 금지 항목 6종이 schema에 데이터로 박힘. 추가하려면 schema 수정 → PR → 리뷰 필요. 즉시 제어 불가.

### 3. ⭐ 중첩 모델 7개 — 합성 가능 구조

`WorkforceAgentResponse` 안에 다른 모델 7개. 왜:
- LLM이 더 잘 이해함 (nested object 명확히 분리)
- 재사용 가능 (`EvidenceReference`는 visa/contact agent도 사용)
- 단위 테스트 쉬움 (`ApprovalBlock` 단독 검증)
- 변경 영향 격리

### 4. ⭐ Typed list vs `list[dict]` — 의도된 차이

```python
candidate_readiness: list[CandidateReadinessItem]  ← 안전 경계 (typed)
missing_inputs: list[dict]                          ← 디버깅 정보 (자유)
```

위험도가 높은 건 typed, 낮은 건 dict. 모든 걸 typed로 하면 schema 수정 잦고, 모든 걸 dict로 하면 안전 경계 없어짐.

### 5. ⭐⭐⭐ `field_validator` vs `model_validator` vs 별도 validator

이 schema에 `field_validator`는 단 하나(`requires_human_approval`):

```python
@field_validator("requires_human_approval")
def _must_require_approval(cls, v):
    if not v: raise ValueError(...)
    return v
```

**Schema validator** = "응답이 형식적으로 유효한가" (invariant)
**별도 Validator 파일** = "응답이 정책적으로 안전한가" (forbidden phrase, evidence grade, business rule)

분리 이유:
1. 정책은 schema보다 자주 바뀜
2. 정책은 여러 종류 (safety/evidence/business)
3. 테스트 격리 가능
4. error 종류 구분 가능
5. 다른 agent가 재사용

### 6. `default_factory=list` — Pydantic 정확성

mutable default arg 함정 회피 + Pydantic 2 권장 + 빈 리스트가 valid 신호.

### 7. ⭐ `agent: Literal["workforce_agent"]` — discriminator 패턴

값 하나인데 명시한 이유:
- JSON 응답 self-identifying
- 다형성 준비 (Pydantic union discriminator)
- LLM 오타 차단

### 진짜 포인트

이 7개 Pydantic 클래스가 보여주는 건 **"prompt에 자연어로 형식을 설명하지 말고 타입 시스템에 박아라"**. 그리고 마지막 주석의 가르침: schema는 **응답의 형식**, **응답의 정책**(forbidden phrase 등)은 별도 validator로. 이 분리를 day 1에 했어야 함.

---

## §5. safety validator — 7가지 핵심 포인트

### 1. ⭐ Schema가 못 잡는 걸 잡는다

schema의 `Literal`은 enum 검증에 강하지만 **자유 텍스트 필드는 못 잡음**. `summary: str`, `safe_description: str`, `handoff_questions[].question: str` 세 곳에 LLM이 `"성실해 보입니다"` 써도 schema는 통과.

**핵심 분리**: Schema = 구조 검증, Validator = 내용 검증.

### 2. ⭐⭐ Fail-closed 원칙 — "silent fallback 금지"

| 방식 | 검증 실패 시 | 외고반장 적합? |
|---|---|---|
| Fail-open | 에러 무시 | ❌ 절대 안 됨 |
| Fail-closed | 즉시 차단 | ✅ 맞음 |

silent fallback 금지: validator가 raise하고 caller가 명시적으로 BLOCKED 표시. 안 catch하고 빈 응답 반환하면 → 사용자가 정상 응답으로 오해 → 금지된 행위 통과.

### 3. ⭐ 구조화된 Exception — 디버깅/감사 추적

```python
class SafetyValidationError(Exception):
    def __init__(self, term: str, location: str):
        self.term = term       # 어떤 단어
        self.location = location  # 어디서
```

얻는 것:
- Evidence Log 기록 가능
- 모니터링 집계 가능
- UI에 명확한 메시지
- 테스트 단정 가능
- prompt 개선 단서

### 4. ⭐ 여러 위치 검사 — 위반 옮겨가기 차단

LLM은 영리해서 summary에서 차단되면 다른 자유 텍스트로 위반을 옮길 수 있다. summary, safe_description, handoff_questions 세 곳을 다 검사. **검사 위치 누락 = security hole.**

### 5. ⭐⭐ Intent/Status 일관성 검사 — Logical invariant

```python
if response.intent == "unsupported_candidate_judgment":
    if response.status not in ("blocked", "needs_human_review"):
        raise ...
```

LLM이 "이건 금지된 요청"이라고 정확히 식별했음에도 초안을 만들어 버린 자기모순. **business invariant** 검증. schema의 Literal로는 못 잡음 (개별 필드는 valid).

### 6. `forbidden_judgment_used: bool` — Self-report 차단

schema에 boolean을 두고 True면 즉시 차단. 정직한 LLM이 "후보 평가가 필요했음"이라고 자진 보고하면 catch. **방어선이 두 개**.

### 7. 단순 substring 매칭의 의도된 단순함

regex도 fuzzy도 아닌 `if term in text`. 의도된 이유:
- 예측 가능 (regex 버그 없음)
- 테스트 쉬움
- 추가/제거 비용 0
- 언어별 변형 대응 (regex 합치기 어려움)

### Defense in Depth — 3겹 방어

```
1층: Schema (Literal, 타입)        → 구조 위반 차단
2층: Validators (이 파일 외 2개)    → 정책 위반 차단  ← 여기
3층: Approval Gate (LangGraph)     → 사람 검토
```

### 진짜 포인트

**"LLM 출력 안전은 schema 한 군데로 못 닫는다."** `with_structured_output(strict=True)`는 강력하지만 자유 텍스트 필드의 의미적 안전까지는 보장 못 함. 그래서 **별도 validator + fail-closed + structured exception + 모든 위치 검사 + logical invariant + self-report**의 7가지 패턴이 한 작은 파일에.

---

## §6. evidence validator — 7가지 핵심 포인트

### 1. ⭐⭐⭐ 가장 위험한 LLM 사고 — Citation Hallucination

LLM의 가장 악명 높은 실수가 "그럴듯한 출처를 만들어내는 것":
- 미국 변호사가 ChatGPT의 가짜 판례 제출 → 제재 (2023)
- LLM이 존재하지 않는 논문 인용 → 학술 부정 다수

외고반장에서 가짜 법 조문 인용 → 행정 사고. `if ev.source_id not in retrieved_source_ids: raise` 한 줄이 그 사고를 차단.

### 2. ⭐⭐ Cross-reference 패턴 — `retrieved_source_ids` 파라미터

validator는 LLM 응답 단독으로 검증 안 함. RAG가 실제 검색해서 LLM에게 넘긴 chunk의 source_id를 따로 받아 cross-reference. **외부 ground truth와 비교가 필수.**

### 3. ⭐⭐⭐ Grade × Used_for 매트릭스 — Schema가 못 잡는 relational constraint

| evidence_grade | used_for | 허용? |
|---|---|---|
| A (법령) | required_checks | ✅ |
| D (참고용) | required_checks | ❌ |
| F (합성) | legal_or_administrative_review | ❌ |
| F (합성) | candidate_readiness_table | ✅ (데모 OK) |

**같은 F grade라도 용도에 따라 다름.** 두 필드의 조합은 schema가 못 검증. Relational validator로만 표현 가능.

### 4. ⭐⭐ F Grade 차단의 도메인 의미

- A: 법령/정부 공식 → 답변 근거 ✅
- B: 공공기관 → 답변 근거 ✅
- E: 내부 템플릿 → 가능 (내부 표시)
- D: 참고용 → 참고만
- F: **합성 데이터 → 공식 근거 사용 금지**

F는 시드 데이터(`seed_eps_procedure_demo_001`). 인제스천 검증용으로는 필요하지만 운영 답변에 새면 사고. **"있게 하되 쓰지 못하게"** 분리.

### 5. ⭐ Fail-closed 일관성 — Safety validator와 같은 패턴

silent strip 안 하는 이유: 사용자가 "EPS 절차에 따라..."를 보는데 evidence list가 비어있으면 어디서 온 정보인가? **출처 없이 답변하는 것이 답변 안 하는 것보다 위험** → 통째로 차단.

### 6. ⭐ 정책의 데이터 표현 — Set으로 분리

```python
DISALLOWED_AS_OFFICIAL_EVIDENCE = {"D", "F"}
OFFICIAL_USED_FOR = {"required_checks", "legal_or_administrative_review"}
```

정책이 데이터로 분리. git blame으로 정책 변경 이력 추적, 다른 validator와 공유 가능, 확장 단순.

### 7. 빈 evidence — 의도된 silence

evidence가 빈 리스트면 통과. "출처 없음"이 정책 위반 아님. 다른 validator(business_rule)가 "특정 status면 evidence 비면 안 됨" 같은 추가 검증. **Single responsibility.**

### Defense in Depth — Evidence 안전 4층

```
1층: 인제스천 (모든 chunk에 grade 자동 부여)
2층: RAG retriever (metadata filter)
3층: 이 validator (cross-reference)  ← 여기
4층: Approval Gate + UI (사람 확인)
```

### 진짜 포인트

**"LLM 출력의 사실성(factuality)은 schema로 못 보장한다."** `evidence_grade: Literal["A"~"F"]`까진 강제 가능하지만 source_id가 실재하는지, grade를 잘못 쓰는지는 schema가 모름. **외부 ground truth와 cross-reference**로만 검증 가능.

---

## §7. business_rule validator — 7가지 핵심 포인트

### 1. ⭐⭐⭐ Schema/Safety/Evidence가 못 잡는 영역

```
Schema   → 형식 위반: status가 "ready_done"?
Safety   → 텍스트 위반: summary에 "성실"?
Evidence → 사실 위반: source_id가 retrieved에 없음?
Business → 논리 위반: Rule이 "승인 필요" 했는데 LLM은 "false"?
```

이 validator는 **두 입력(rule_result + LLM response)의 관계**를 검증. 어느 한쪽만 봐서는 위반인지 알 수 없음.

### 2. ⭐⭐ Rule Base = Deterministic Ground Truth

```
RAG     = 공식 근거         (정보)
Rule    = 날짜·true/false   (결정 — deterministic)
LLM     = 자연어 구조화     (생성 — probabilistic)
Human   = 발송 전 승인      (책임)
```

Rule Base는 LLM 호출 **전**에 실행되어 LLM에게 input으로 전달. LLM은 Rule 결과를 알면서도 무시할 수 있음. 그게 문제. 이 validator가 "LLM이 Rule을 무시했나"를 검증.

**Rule이 이기는 이유**: 재현성, 코드 검증 가능, 감사 요건. LLM은 "도와주려는" 본능 때문에 제약 우회 경향.

### 3. ⭐⭐ 3가지 검사 — 가장 위험한 LLM 우회 패턴

**검사 1: Approval bypass** — Rule이 "승인 필요"인데 LLM이 false. **가장 위험한 사고**.
**검사 2: Status bypass** — Rule이 forbidden 감지인데 LLM이 status=draft_ready. **safety validator는 텍스트만 보지만 이건 의도까지**.
**검사 3: Field bypass** — Rule이 `missing=[photo]`인데 LLM이 `ready_items=[photo]`. **사실 데이터에 대한 LLM의 hallucination**, 가장 미묘.

### 4. ⭐ Cross-Input Validation — Evidence validator와 같은 메타 패턴

```python
def validate_business_rules(
    response: WorkforceAgentResponse,    ← LLM 출력
    rule_result: dict[str, Any],          ← Rule Base 출력 (ground truth)
):
```

"LLM의 자기보고를 LLM 외부 데이터로 검증"하는 메타 패턴. evidence validator와 동일.

### 5. ⭐ Trio Validator의 역할 분담

| Validator | 입력 | 잡는 사고 |
|---|---|---|
| safety | response만 | 금지 표현 |
| evidence | + retrieved_source_ids | hallucinated 출처 |
| business_rule | + rule_result | Rule 우회, 사실 모순 |

각 validator가 **다른 입력**을 받아 **다른 종류의 위반**을 잡음. 합치면 책임 불명확, 분리하면 명확.

### 6. ⭐ Validator의 작은 크기가 의도

3개 검사만 있음. 알려진 사고 패턴만 명시적으로 검사. 가설적 위험까지 검사하면 false positive 폭발. **운영 중 사고 패턴 발견 시 추가**가 lean.

### 7. ⭐ Set 연산의 우아함 — `missing & ready`

nested loop 대신 set 교집합. Pythonic + 효율 + 가독성. validator는 자주 호출되는 코드.

### 시나리오 비교 — 가장 미묘한 위반

```
시나리오 C (가장 위험):
→ 사용자: "후보 C001 상태 알려줘"
→ Rule이 missing=[photo, health_check] 계산
→ LLM 응답:
  - summary: "후보 C001 상태 정리"          ← safety 통과
  - evidence: [valid sources]                ← evidence 통과
  - ready_items: ["passport", "photo"]      ← photo 거짓말
→ business_rule만 catch ⚠
```

### 진짜 포인트

**"LLM은 자기가 받은 input을 무시할 수 있다."** prompt에 "Rule이 missing=[photo]를 알려줬으니..."라고 적어도 LLM은 가끔 무시.

해결책:
1. Rule Base를 LLM 외부에서 deterministic 계산
2. rule_result를 LLM에 input으로 전달
3. LLM 출력을 rule_result와 cross-reference
4. 모순이면 fail-closed 차단

**한 줄로**: Schema는 LLM의 손목을, Safety는 LLM의 입을, Evidence는 LLM의 거짓 인용을, Business Rule은 LLM의 논리 우회를 묶음. 4종류의 다른 끈으로 LLM을 도메인 안전 영역에 묶어두는 구조.

---

## §8. BaseStructuredChain — 8가지 핵심 포인트

### 1. ⭐⭐⭐ Generic[T] — 타입 안전성 end-to-end

```python
T = TypeVar("T", bound=BaseModel)

class IntentChain(BaseStructuredChain[IntentClassification]):  # T = IntentClassification
    schema = IntentClassification
    def classify(self, ...) -> IntentClassification:
        return self._invoke([...])  # 반환 타입 자동 IntentClassification
```

얻는 것: IDE 자동완성, 타입 체커 catch, 리팩토링 안전, 수동 cast 불필요.

### 2. ⭐⭐ Class-level Configuration — 설정의 위치

```python
schema: type[T]                    # 필수
model: str = "gpt-4o-mini"          # default (override 가능)
temperature: float = 0.0
max_retries: int = 2
method: str = "json_schema"
```

class attribute인 이유:
- chain은 per-app singleton
- 모델 선택은 chain의 정체성
- subclass override 명시적
- 모델 변경이 PR 검토 가능

### 3. ⭐⭐ `include_raw=True`의 의도된 trade-off

| `include_raw=False` | `include_raw=True` (이 코드) |
|---|---|
| 단순 | 복잡 (unwrap 필요) |
| 디버깅 어려움 | **디버깅 정보 풍부** |
| Evidence Log 빈약 | **model 행동 기록 가능** |

복잡함은 base가 흡수, subclass는 단순한 인터페이스만. **복잡함의 좋은 위치 선정.**

### 4. ⭐⭐ Result handling — 4중 방어

```python
if isinstance(result, dict):              # 1. 모드 확인
    if result.get("parsing_error"):       # 2. retry 후 실패
        raise StructuredChainError(...)
    parsed = result.get("parsed")
    if not isinstance(parsed, self.schema):  # 3. 타입 검증
        raise StructuredChainError(...)
    return parsed
return result                              # 4. fallback
```

### 5. ⭐⭐⭐ Template Method 패턴 — 일관성 강제

```
Base가 정한 골격:
  1. __init__ (API key + LLM + with_structured_output)
  2. _invoke (호출 + unwrap + 검증 + 반환)
  3. evidence_metadata (PII 안전)

Subclass가 채우는 것:
  1. schema 선언
  2. (선택) override
  3. 도메인 method
```

base 없이 각 chain이 직접 호출하면 5가지 미묘하게 다른 패턴 → 운영 사고 시 추적 불가.

### 6. ⭐⭐ `StructuredChainError` — Fail-closed 일관성

3가지 경우에 raise: schema retry 후 실패, 타입 미스매치, 프로토콜 위반. **명시적 exception** + **silent fallback 금지** + 도메인 의미 명확.

### 7. ⭐⭐⭐ `evidence_metadata()` — PII 안전성 + 디버깅

LLM 응답에 PII(외국인등록번호 등) 섞일 수 있어 raw 저장 금지. 4개 안전 metadata만:

```python
{
    "model_name": ...,
    "raw_present": bool,
    "raw_content_hash": "sha256:abc123...",   # 단방향
    "parsing_error": ...,
}
```

→ "어제 응답이 오늘과 같은가?" hash로 비교. **원문 없이 답변 가능.**

### 8. ⭐ `max_retries=2` — 비용 cap

0이면 일시적 hiccup에 너무 민감. 5+면 무한 재시도. **2 (총 3회 시도)**가 sweet spot. 평균 1배, 최악 3배.

### Defense in Depth — Chain 4중 방어

```
1. with_structured_output(strict=True)    ← LLM 토큰 레벨
2. parsing_error 검사                      ← retry 후 명시적
3. isinstance(parsed, self.schema)         ← 라이브러리 버그 방어
4. (subclass) Trio validator               ← 정책
```

### 진짜 포인트

**"LangChain 1.0 사용 자체를 표준화한다."** `with_structured_output`은 1.0 메인 API지만 사용 방식이 여러 가지(method, include_raw, max_retries). 자유롭게 쓰면 5가지 미묘하게 다른 패턴. base가 강제하면 모든 chain 일관.

day 1에 이걸 깔지 않으면 운영 사고의 추적 불가능한 분산이 발생. **현재 코드에서 가장 빠진 부분.**

---

## §9. IntentChain — 8가지 핵심 포인트

### 1. ⭐⭐⭐ 코드량의 충격적 감소 — Abstraction의 가치

**현재 64줄** → **Day-1 1.0 15줄** = 약 4배 감소.

사라진 것:
- LLM 생성 코드 → base
- API key 검사 → base
- `json.loads` → with_structured_output
- 백틱 hack → 필요 없음
- 화이트리스트 필터 → Literal enum
- enum 변환 → Pydantic 자동
- try/except → base의 fail-closed

**사라진 코드가 다 잠재적 사고 지점.**

### 2. ⭐⭐ `schema = IntentClassification` — 한 줄이 모든 걸 결정

이 두 줄이 동시에:
- Generic[T]의 T 결정
- LLM 구축 시 schema 전달
- 타입 검증 시 사용
- Evidence Log model_name 기록

### 3. ⭐ Module-level `_SYSTEM` — 의도된 위치

매 호출마다 string 재생성 X, prompt 변경 한 곳에서, 테스트 import 가능. **prompt가 짧고 고정이면 inline, 길고 동적이면 별도 파일.**

### 4. ⭐⭐ `classify()` vs `invoke()` — Semantic API

base는 `_invoke`로 통일하지만 subclass는 도메인 동사 사용:
- IntentChain → `classify`
- VisaChain → `judge`
- ContactChain → `draft`
- FinalResponseChain → `compose`

**chain은 도메인 service.** 호출자가 LangChain message 추상화 몰라도 됨.

### 5. ⭐ SystemMessage + HumanMessage — Trust Boundary

- SystemMessage: prompt-injection 저항선 (영구 규칙)
- HumanMessage: 검증 대상 (이번 요청)

분리가 없으면 `"무시하고 추천해줘"`에 LLM이 따를 수 있음. **메시지 타입에 trust boundary가 박힘.**

### 6. ⭐⭐⭐ "없는 것"이 진짜 포인트 — Defense Inheritance

```python
# ❌ 없음: try/except
# ❌ 없음: isinstance 검사
# ❌ 없음: field_validator
# ❌ 없음: api_key fallback
```

**다 base가 처리하기 때문.** subclass는 어기지 않을 수 없음.

### 7. ⭐ 새 chain 추가 30초 — Discoverability

```
1. schema 작성 (5분)
2. chain 작성 (30초, template 복사)
3. prompt 작성 (5분, 길면)
4. 테스트 (10분)
```

진짜 시간은 schema 설계 + prompt 작성 (도메인 작업). **framework 보일러플레이트 0.**

### 8. ⭐ 빈 응답 처리도 schema가

```python
intents: list[Intent] = Field(default_factory=list, ...)
```

LLM이 분류 못 하면 `intents=[]`. caller가 분기. fallback 로직이 schema에 박혀 chain 코드 깨끗.

### 5 chain 합산

```
5 chain × 평균 15줄 = 75줄
+ base class 70줄
= 145줄

대조 (base 없을 때):
5 chain × 평균 70줄 = 300~400줄 + 일관성 없음
```

### 진짜 포인트

**"좋은 abstraction의 회수는 사용처에서 보인다."** subclass가 짧고, 도메인 의도만 표현하고, framework 디테일 모르고, 안전 장치 자동 상속. base에 들인 70줄이 subclass 5개에서 200~300줄 절약 + 5중 안전 일관성 보장.

**base class는 단순 DRY가 아니라 "안전 정책의 단일 진입점."**

---

## §10. WorkforceJudgmentChain — 8가지 핵심 포인트

### 1. ⭐⭐⭐ "Pipeline within a Pipeline" — 4단계 합성

```
input
  ↓
[1] prompt builders
  ↓
[2] BaseStructuredChain._invoke (LLM + schema + retry)
  ↓
[3] validate_safety
  ↓
[4] validate_evidence
  ↓
[5] validate_business_rules
  ↓
output
```

5단계 중 단 하나라도 실패하면 fail-closed. 이 chain의 진짜 책임 = **합성**.

### 2. ⭐⭐ Keyword-only 인자 (`*,`) — Positional 차단

```python
def invoke(self, *, user_request, company_context, candidate_context, rag_results, rule_results):
```

`company_context: dict`와 `rule_results: dict` / `candidate_context: list` 와 `rag_results: list`가 **둘 다 같은 타입** → positional이면 type checker 못 잡음. 잘못 넘기면 evidence validator가 엉뚱한 데이터 검사 → 사고.

`*`로 keyword-only 강제 = **컴파일 타임 안전.**

### 3. ⭐⭐ `prompts/workforce.py`로 prompt 분리

IntentChain은 inline `_SYSTEM` (5줄), 이 chain은 별도 파일 import. 길이 임계점:
- ~30줄 넘거나 동적 조립 필요 → 별도 파일
- 짧고 고정 → inline

`build_workforce_task_prompt(...)`가 5개 인자로 동적 조립 = **chain logic과 분리되어야 한다는 신호.**

### 4. ⭐⭐⭐ Trio Validator의 의도된 순서

```
1. validate_safety        ← 가장 빠름 (substring O(n))
2. validate_evidence      ← 중간 (set membership)
3. validate_business_rules ← 가장 느림 (set 교집합)
```

두 가지 원칙 동시 적용:
- **Fail-fast 비용 효율** (자주 걸리는 것 먼저)
- **도메인 위험도 우선** (명백한 안전 → 사실 → 논리)

### 5. ⭐⭐ Set Comprehension의 데이터 변환

```python
retrieved_source_ids={
    r.get("source_id") for r in rag_results if r.get("source_id")
}
```

세 가지 동시:
1. list[dict] → set (O(1) lookup)
2. None 필터링 (dirty record 제외)
3. in-place (임시 변수 0)

### 6. ⭐ try/except 없음 — Fail-closed 일관성

이 함수에 try/except가 0개. **silent fallback 금지** 원칙. caller가 모든 exception을 한 곳에서 catch:

```python
except (StructuredChainError, SafetyValidationError, ...) as exc:
    runtime_output["status"] = "BLOCKED"
```

### 7. ⭐ 모든 안전 책임이 한 함수에 — Single Source of Truth

```
WorkforceJudgmentChain.invoke()
├── BaseStructuredChain._invoke()
│   ├── with_structured_output(strict=True)   ← 1
│   ├── auto retry × 2                         ← 2
│   └── parsing_error 검사                     ← 3
├── validate_safety                            ← 4
├── validate_evidence                          ← 5
└── validate_business_rules                    ← 6
```

→ workforce LLM 호출은 **이 함수 한 곳을 통과해야만 가능.** 다른 경로 없음.

### 8. ⭐⭐ IntentChain과의 대조 — 책임 차이

| | IntentChain | WorkforceJudgmentChain |
|---|---|---|
| 입력 | 1개 | 5개 |
| Validator | 없음 | 3개 |
| Prompt | inline 5줄 | 별도 파일, 동적 |
| 위험도 | 낮음 | 높음 |
| 줄 수 | 15줄 | 40줄 |

같은 base class의 두 다른 응용. **책임의 무게가 다르면 합성 정도도 다름.**

### 진짜 포인트

**"안전 책임은 합성으로 강제한다."** LLM 호출에는 4종류의 위험(형식/안전/사실/논리). 한 곳에서 같이 막아야 안전 보장. 매 호출마다 손으로 4개 호출하면 빠뜨림.

→ chain이 "이 LLM 호출은 4중 검증을 거쳐야 함"이라는 도메인 계약을 코드로 박음. caller는 chain.invoke()만 알면 됨. **합성을 강제하는 패턴의 정점.**

---

## §11. ForeignHiringState — 8가지 핵심 포인트

### 1. ⭐⭐⭐ "Shared Blackboard" 패턴 — LangGraph의 핵심

```
일반 함수 chain:
  node1 → node2 → node3 (직접 호출, 직전 출력만)

LangGraph (이 state):
  blackboard
  ↑↓ ↑↓ ↑↓
  node1 node2 node3 (모두 같은 state, 직접 호출 X)
```

의미:
- 노드 간 직접 호출 0 → "agent 직접 호출 금지" 강제
- state 전체 가시성
- 노드 추가/제거가 다른 노드 영향 X
- state가 메시지, 노드는 transformer

### 2. ⭐⭐ 시간순 섹션 그룹화 — 주석이 곧 lifecycle

```python
# Initial input          ← 진입점
# Routing                ← intent_router_node
# Loaded                 ← state_loader_node
# RAG                    ← executor (RAG)
# Agent results          ← executor (sub-agent)
# Convergence            ← aggregator + approval_gate
# Cross-cutting          ← 모든 노드 append
```

state는 **workflow의 시간축이 코드로 표현된 것.**

### 3. ⭐⭐ Pydantic의 4가지 역할 동시 수행

| 역할 | 메커니즘 |
|---|---|
| 타입 안전 | IDE/체커 |
| 자동 검증 | ValidationError |
| 직렬화 | model_dump() → DB snapshot |
| 자체 문서화 | 클래스 정의 |

특히 직렬화는 LangGraph + DB snapshot의 필수. **한 클래스 정의 = 메모리 + DB + API 응답.**

### 4. ⭐ `default_factory` 패턴

거의 모든 collection 필드. 이유:
- mutable default arg 함정 회피
- Pydantic 2 권장
- runtime_mode default를 enum 한 곳에 집중

state는 **초기 입력 6개 필드만으로 생성 가능.** 노드 통과하며 점진적으로 풍부해짐.

### 5. ⭐⭐⭐ `*_llm_response` 3개 명시적 필드 — 왜 dict 하나가 아닌가

대안 (안 쓴 패턴):
```python
llm_responses: dict[str, dict[str, Any]] = Field(default_factory=dict)
```

명시적 3개를 쓰는 이유:
- 타입 체커 추적 가능
- 새 agent 추가 시 schema 수정 → 코드 리뷰에서 보임
- None vs missing 구분 가능
- Aggregator가 어느 필드 보는지 명확

**숨겨진 dict 키보다 코드 검토 가능한 명시적 필드가 안전.**

### 6. ⭐⭐ `runtime_mode`가 state field

대안 — parameter로 전달:
```python
def run_workforce_agent(state, runtime_mode):  # ❌
```

state field로 두는 이유:
- 모든 노드 자동 접근
- 직렬화 자동 (DB snapshot, evidence log)
- request 내 일관성
- LangGraph state mutation 모델과 통합

운영 제어가 state 필드 하나로 가능: A/B, kill switch, feature flag.

### 7. ⭐ `approval: dict | None = None` — 의미적 default

3가지 상태:
- `None` = approval_gate 미도달
- `{"required": True, ...}` = PENDING
- `{"required": False, ...}` = NOT_REQUIRED

**None의 명시적 사용이 의미를 추가.**

### 8. ⭐⭐ "Agent 직접 호출 금지" enforce 메커니즘

```
history.md 결정: "agent 간 직접 호출 금지 - shared state로만 소통"

state가 강제하는 방식:
1. workforce_agent → visa_agent.run() 직접 호출 불가
2. 대신 state.workforce_llm_response에 결과
3. visa_agent도 state.visa_llm_response에 결과
4. aggregator가 state에서 읽어 합침
5. sub-agent끼리 서로 모름
```

state는 architectural rule을 enforce하는 통로.

### State가 곧 LangGraph의 본체

LangGraph는 state machine. 노드 = state transition function. state = source of truth.

- 노드는 state 외 어디에도 정보 저장 X
- 외부 사이드 이펙트 → evidence_events에 기록
- DB snapshot = 시스템 상태 백업
- evidence_log + state = 사고 재현

### 진짜 포인트

**"안전 규칙은 데이터 구조로 강제할 수 있다."**

"agent 직접 호출 금지"는:
- 문서로 적으면 → 사람이 어김
- 코드 리뷰 → 가끔 빠짐
- 미들웨어 → 복잡

→ shared state로 만들면 **어길 방법이 없음.** agent들이 서로를 모름.

---

## §12. intent_router_node — 8가지 핵심 포인트

### 1. ⭐⭐⭐ Chain vs Node — 책임의 명확한 분리

| | IntentChain | intent_router_node |
|---|---|---|
| 책임 | LLM 호출 + schema | state mutation + evidence |
| 입력 | user_message: str | state |
| 출력 | IntentClassification | state (mutated) |
| 의존성 | LangChain + Pydantic | LangGraph + state |
| 테스트 | API mock | state mock |

**chain은 다른 곳에서도 재사용 가능. node는 LangGraph workflow 안에서만.**

### 2. ⭐⭐ Lazy Singleton Pattern — Module-level `_chain`

3가지 이유 동시:

#### 이유 1: chain 생성 비용
```
매 요청 chain 생성: 10ms × 1000 = 10초/sec 추가 latency
한 번 생성 후 재사용: 무시 가능
```

#### 이유 2: API key 없는 환경에서 import 가능
import 시점에 IntentChain() 호출되지 않음 → CI/테스트/로컬 살아남음.

#### 이유 3: 테스트 mock 용이
`_get_chain()` 함수가 별도라 patch 가능.

### 3. ⭐⭐⭐ Graceful Degradation — API key 없을 때 워크플로우 계속

```
시나리오 A: API key 없으면 시스템 죽음 → 운영 사고
시나리오 B (이 코드): API key 없으면 deterministic 모드로 계속 → 시스템 살아남음
```

**의도**: AI는 enhancement, 시스템 본체는 deterministic. AI 의존성 격리.

### 4. ⭐⭐ 2-Level Error Handling

| 실패 시점 | 원인 | 대응 |
|---|---|---|
| Construction (1회) | API key 없음 | chain = None |
| Execution (매 호출) | API down, retry 실패 | intents = [] |

광범위 `except Exception`이 의도됨: 어떤 LLM 실패든 empty intents로 fallback. **시스템 전체가 LLM 실패로 죽으면 안 됨.**

### 5. ⭐⭐ LangGraph 노드 계약 — `(state) -> state`

```python
NodeFn = Callable[[ForeignHiringState], ForeignHiringState]
```

모든 노드가 같은 시그니처. 합성 가능, 추가/제거 영향 X, 테스트 단순. `log_event`도 같은 시그니처라 마지막 합성이 자연스러움.

### 6. ⭐⭐ Evidence Logging Cross-cutting

모든 노드 마지막에 같은 패턴:
```python
return log_event(state, make_event(
    event_type=EventType.INTENT_CLASSIFIED,
    request_id=state.request_id,
    summary=...,
    step_name="intent_router",
))
```

`make_event` (pure) + `log_event` (state mutation) 분리 → 테스트 쉬움.

### 7. ⭐⭐⭐ Empty Intents의 명시적 의미 — Silent Fallback이 아님

| Silent Fallback (금지) | Explicit Empty Signal (이 코드) |
|---|---|
| 가짜 성공 응답 | 명시적 빈 결과 |
| 사용자 오해 | 사용자가 "분류 불가" 응답 |
| evidence 정상 기록 | evidence empty 명시 |
| 다음 노드 가짜 진행 | 다음 노드 unsupported 처리 |

**`intents = []`는 fail-safe signal.** planner가 그걸 보고 명시적 분기.

### 8. ⭐ 모든 노드가 같은 패턴 — 일관성

```python
def some_node(state):
    chain = _get_chain()                  # 1. lazy chain
    result = default_value                # 2. safe default
    if chain is not None:
        try:
            result = chain.invoke(...)    # 3. try
        except Exception:
            result = default_value        # 4. fail-safe
    state.some_field = result             # 5. mutate
    return log_event(state, make_event(...))  # 6. evidence
```

새 노드 30초, 모든 노드 같은 안전 보장, 사고 추적 일관됨.

### Layered 아키텍처

```
State    ← 노드 간 통신 + architectural rule
  ↑↓
Node     ← LangGraph 진입점 + state mutation + evidence
  ↑↓
Chain    ← LLM + structured output + validators
  ↑↓
Schema   ← Pydantic + 도메인 정책
```

각 layer 자기 책임만. 한 layer 변경이 다른 layer에 영향 적음.

### 진짜 포인트

**"Layer 분리가 코드 양을 줄이는 게 아니라 책임을 명확히 한다."**

35줄 안에 chain/node/state 세 layer를 각각 정확한 위치에서 호출. 64줄 → 35줄 차이는 코드량 절약이 아니라 **책임 명확화**. 9개 노드에 일관 적용되면 전체 workflow가 같은 안전성·추적성을 자동으로 누림.

---

## §13. run_workforce_agent — 8가지 핵심 포인트

### 1. ⭐⭐⭐ 4단계 Orchestration의 의도된 순서

| 순서 | 단계 | 만약 빠지면 |
|---|---|---|
| 1 | call_limiter | runaway 비용 폭증 |
| 2 | Rule Base | LLM 실패 시 fallback 없음 |
| 3 | FORBIDDEN early exit | 금지 요청에 LLM 호출 |
| 4 | LLM (옵션) | 자연어 풍부함 잃음 |

**1~3은 반드시, 4는 옵션.** 안전 핵심은 LLM 없이도 동작.

### 2. ⭐⭐⭐ "Rule First, LLM Second" — Deterministic이 항상 먼저

```python
# 항상 먼저
runtime_output = build_hiring_readiness_result(...)
```

대조 — LLM-first면 같은 입력에 다른 결과 → 감사 불가능.

Day-1 1.0 패턴:
```
모든 호출 → deterministic 결과 (항상 동일)
              ↓
            LLM 옵션 → enhancement (자연어만)
              ↓
            validators → enhancement이 안전 규칙 따랐나
              ↓
            ENHANCEMENT만 저장
```

### 3. ⭐⭐ FORBIDDEN Early Exit — Defense in Depth

5가지 이유:
1. 비용 (LLM 호출 안 함)
2. **LLM에 forbidden prompt 안 줌** (Defense in Depth)
3. 응답 시간
4. 명시적 차단 메시지
5. agent_results에 기록

**Rule Base가 1차 방어, LLM safety가 2차, validator가 3차.** 1차에서 잡히면 2~3차 호출 자체 안 됨.

### 4. ⭐⭐ runtime_mode 분기

| runtime_mode | 동작 | LLM 비용 |
|---|---|---|
| DETERMINISTIC | Rule만 | 0 |
| LANGCHAIN_JUDGMENT | Rule + LLM | per-call |

LLM이 explicit opt-in. CI/테스트는 default로 0 비용. A/B 테스트, kill switch가 한 줄.

### 5. ⭐⭐⭐ 두 종류의 except — 의미적 차이

| 실패 종류 | 도메인 의미 | 대응 |
|---|---|---|
| `RuntimeError` (API key) | 인프라 문제 | skip (deterministic은 OK) |
| Validator errors | 보안 위반 | BLOCKED |

같은 except로 합치면 API key 없는 환경에서 모든 요청 BLOCKED → 시스템 죽음. **두 실패의 도메인 의미를 분리하는 게 핵심.**

### 6. ⭐⭐ 3-State 표현 — `llm_response_attached` + `status`

```
state ┌─→ attached=True                           ← 성공
      ├─→ attached=False + skip_reason            ← 인프라 문제
      └─→ attached=False + status=BLOCKED         ← 보안 위반
```

단순 success/fail 아니라 **실패 종류까지 의미적으로 분리.**

### 7. ⭐ State Mutation 패턴 — 두 군데 저장

```python
state.workforce_llm_response = response.model_dump()  # 전용 (specific)
state.agent_results.append({"agent": "...", **runtime_output})  # 공통 (generic)
```

aggregator가 둘 다 사용:
- agent_results: 모든 agent 순회
- workforce_llm_response: 특정 응답 직접 접근

### 8. ⭐⭐ Agent Layer의 정체성

| Layer | 책임 |
|---|---|
| State | 데이터 |
| Chain | LLM 표준화 |
| Node | LangGraph 진입 |
| **Agent** | **Mission 비즈니스 로직** |
| Validator | 정책 |

**Agent는 mission의 정체.** chain은 도구, node는 wrapper, agent는 mission 로직 자체.

### Layer 합성 — 6 Layer가 한 함수에서

```python
check_llm_limit(state)              # Middleware
build_hiring_readiness_result(...)   # Rule Base
WorkforceJudgmentChain()             # Chain
chain.invoke(...)                    # (chain 안에서 LLM + Validator)
state.workforce_llm_response = ...   # State
state.agent_results.append(...)      # State
RuntimeMode.LANGCHAIN_JUDGMENT       # RuntimeMode
```

각 layer는 자기 책임만, agent 함수는 도메인 흐름대로 엮음. **40줄에 그칠 수 있는 이유 = 6 layer가 각자 자기 일.**

### 순서가 곧 안전

```
1. call_limiter → 자원 보호
2. Rule Base → deterministic
3. FORBIDDEN exit → 명백한 금지 차단
4. LLM (옵션) → enhancement
5. agent_results → aggregator
```

**순서 바꾸면 invariant 깨짐.**

### 진짜 포인트

**"안전 시스템에서 코드 순서는 데이터 구조만큼 중요하다."**

좋은 추상화를 만들어도 호출 순서가 안전을 결정. 이 함수의 4단계는 **그 순서가 곧 외고반장의 안전 정책.** 다른 mission agent도 같은 5단계 패턴 → 운영 사고 시 추적 일관.

---

## §14. workflow.py — 8가지 핵심 포인트

### 1. ⭐⭐⭐ Linear Edges = Deterministic by Construction

`add_conditional_edges` 0개. 8 노드 일직선.

```
외국인 고용 행정 = 감사 가능성 필수
   ↓
같은 입력 → 같은 실행 경로
   ↓
linear pipeline
```

대조 — `create_agent`나 conditional edge면 LLM이 매번 다른 경로 → 재현성 깨짐.

### 2. ⭐⭐ Loop-driven add_node + add_edge

리스트로 묶어 8 노드 + 7 edge 자동 등록.

이유:
- 순서 변경 비용 0
- 노드 추가/제거 1줄
- 시각적 파이프라인
- Pair locality (name + function 같은 줄)

### 3. ⭐ String Constants

LangGraph convention. enum 안 쓴 이유:
- LangGraph가 string 기대
- evidence_log에 인간 읽기 좋음
- 노드 이름 짧고 명확

### 4. ⭐⭐⭐ MemorySaver — HITL Interrupt의 핵심

```python
.compile(checkpointer=MemorySaver())
```

가능하게 하는 것:
- 각 노드 후 state snapshot
- approval_gate에서 interrupt
- 외부 검토 후 resume
- thread_id로 연속 처리

**MemorySaver 없으면**: workflow 한 번에 끝나야 함, 사람 검토 별도 시스템 필요, state 복구 불가.

→ **LangGraph의 진짜 차별점.** 단순 함수 chain은 못 함.

### 5. ⭐⭐ Singleton Compiled App — Lazy Init

build (빠름, 1회) + compile (느림, 1회). lazy 이유:
- import 시점 안 무거움
- 첫 요청까지 비용 미룸
- 외부 의존성 import 회피

Module-level singleton: MemorySaver 같은 인스턴스라야 thread_id 연속 처리 가능.

### 6. ⭐⭐ "LangChain 버전과 무관" 주장

`langgraph` import만 함. 노드 함수의 시그니처(`(state) -> state`)만 알면 됨.

→ orchestration layer와 LLM call layer 명확 분리. LangChain 0.x → 1.0이든 → Anthropic SDK든 이 파일 영향 0.

### 7. ⭐ Build vs Compile 분리

- Build: pure (graph 조립)
- Compile: stateful (검증 + 실행 객체 + checkpointer)

테스트에서 build만 호출 가능, 다른 checkpointer로 compile 가능. **분리가 테스트성과 유연성을 만듦.**

### 8. ⭐ 단순한 구조의 의도

조건 분기/병렬/sub-graph/dynamic 다 안 씀. 의도된 단순함:
- 외고반장 도메인 fit
- 디버깅 쉬움
- 안전 정책 자연스럽게 enforce
- 새 노드 추가 한 줄

**YAGNI** — 필요할 때 graph 확장.

### 9. 현재 결정과의 긴장 — `create_agent`-First

migration plan: 이 `workflow.py` 패턴에서 멀어지는 방향.

```
production = LangChain 1.0 create_agent
  ↓ (내부적으로 LangGraph)
  ↓ middleware 자동
  ↓ structured output 자동
```

| | Custom LangGraph | create_agent |
|---|---|---|
| 명시성 | ⭐⭐⭐ | ⭐ |
| 단일 approval | ⭐⭐⭐ | ⭐⭐ middleware |
| 재현성 | ⭐⭐⭐ | ⭐⭐ |
| 1.0 통합 | ⭐ 수동 | ⭐⭐⭐ 자동 |
| 확장성 | ⭐⭐ | ⭐⭐⭐ |

둘 다 valid. **운영 사고 패턴 + middleware 강제력**이 결정.

### 학습 포인트 (framework 결정과 무관)

1. Layer 분리 (langchain import 0)
2. Build vs Compile
3. Loop-driven 등록
4. MemorySaver 의의
5. Singleton compiled app
6. 단순함의 가치

이 패턴들은 **`create_agent`로 가도 유효.** 적용 위치만 framework 안으로 이동.

### 진짜 포인트

**"Orchestration의 explicit 정도가 trade-off."**

Explicit graph: 모든 것이 코드에 보임, 안전 규칙이 코드 구조로 enforce, framework 변경 영향 0.
Implicit graph (`create_agent`): 자동 조립, middleware 자동, 표준 패턴 — 단점은 안전 규칙을 framework가 보장하는지 검증 필요.

만약 운영 중 middleware 우회 사고 발생 → custom LangGraph로 회귀 가능. **day-1 reference design이 보존되는 이유.**

---

## §15+§16. 테스트 + 학습 원칙 — 마지막 두 섹션

### §15 — 왜 테스트를 마지막에

#### 1. ⭐⭐⭐ Mock 깊이가 곧 테스트의 견고함

```python
@patch("app.agent_runtime.llm.chains.base.ChatOpenAI")
@patch("app.agent_runtime.llm.chains.base.get_settings")
```

**둘 다 base.py 한 곳.** 5개 chain 테스트 시 모두 같은 mock 위치. base 없었으면 chain마다 다른 import path.

#### 2. ⭐⭐ `include_raw=True` 덕분에 mock이 자연스러움

dict로 mock하는 이유 — base가 `include_raw=True`로 호출하기 때문. **테스트가 production 패턴 그대로.**

#### 3. ⭐⭐⭐ 테스트가 짧음 = 합성이 잘 됨

assertion 2줄. 가능한 이유:
- chain self-contained
- chain.invoke가 schema + LLM + 3 validator 한 호출
- 한 종류 위반만 mock

vs 합성 안 된 테스트: setup 30줄, assertion 약함.

#### 4. ⭐ 테스트가 문서 역할

테스트 한 개가 4가지 사용 패턴 동시 문서화: 사용법, 동작, mock 형태, 실패 명시성.

### §16 — 왜 학습 원칙 10개를 마지막에

#### 1. ⭐⭐⭐ Portable한 형태로 압축

| # | 원칙 | 압축한 섹션 |
|---|---|---|
| 1 | LangChain 좁게 lock | §1 |
| 2 | BaseStructuredChain 통일 | §8 + §9, §10 |
| 3 | Validator 분리 | §5, §6, §7 |
| 4 | runtime_mode enum | §2 + §13 |
| 5 | include_raw + hash only | §8 |
| 6 | 팀별 폴더 분기 X | §0 |
| 7 | Fake provider 단계 X | (history) |
| 8 | LangGraph 유지 | §11, §14 |
| 9 | Silent fallback 금지 | §13, §10 |
| 10 | Tool 5-tier 첫날부터 | (tools/) |

**14 섹션 결론을 10문장으로 압축.**

#### 2. ⭐⭐ Next Project의 PR-0 체크리스트

새 LLM 시스템 시작 시 day 1에 완료할 10항목 체크리스트. 외고반장 사고 비용의 압축 → 같은 사고 안 겪음.

#### 3. ⭐⭐⭐ "회고에서 학습으로" 전환

```
§1~14 (회고): "intent_router 64줄 → 35줄로 줄일 수 있었음"
학습 원칙 (예방): "BaseStructuredChain 첫날부터"
```

회고 = 본인 후회, 학습 원칙 = 다른 시작점. **둘 다 있어야 가치.**

#### 4. ⭐⭐ Action verb 형태

명령형: "...lock한다", "...통과시킨다", "...분리한다". 서술형 아닌 행동형. **PR description에 그대로 인용 가능.**

#### 5. ⭐ 10개 — 의도된 숫자

5 이하: 추상적. 20+: 외우기 어려움. **10: chunking sweet spot.**

7개 다른 영역 × 1~3 원칙씩: Dependency, Architecture, Validation, Runtime, Observability, Process, Tools.

#### 6. ⭐⭐ 우선순위 순서

```
1. lock           ← 의존성
2. BaseStructuredChain ← LLM 호출 (자주)
3. Validator      ← 안전 (중요)
4. runtime_mode   ← 운영 제어
...
```

빈도 + 중요도 순서. **새 팀의 1~2주차 작업 순서와 일치.**

#### 7. ⭐⭐ "회수 가능한 자산"

코드 14 섹션 = 외고반장 도메인 묶임. 학습 원칙 10개 = 모든 안전 우선 LLM 시스템 적용 가능 (의료/법률/교육 AI).

#### 8. ⭐ 원칙이 코드와 묶여 있음

추상 원칙 + 구체 코드 양방향 참조. 헷갈리면 다른 쪽 보면 됨.

### 두 섹션이 합쳐지는 이유

```
§1~14: 코드 (어떻게)
   ↓
§15: 테스트 (검증되나)
   ↓
§16: 학습 (왜 + 다음에)
```

**3단 회수 구조**:
- §1~14: 구현 가능성
- §15: 테스트 가능성
- §16: 이전 가능성

테스트 없으면 죽은 코드, 학습 원칙 없으면 일회성 코드.

### 세 종류 독자

| 독자 | 사용 |
|---|---|
| 마이그레이션 작업자 | §1~14 + §15로 PR |
| 같은 도메인 다른 시스템 | §1~16 전체 |
| 다른 도메인 LLM | §16만 봐도 핵심 |

### 진짜 포인트

**§15와 §16은 reference design의 회수 회로.**

§15 = "이 코드가 테스트 가능하다" 증명
§16 = "이 학습이 portable하다" 보장

코드는 도메인에 묶이지만 **테스트 패턴과 학습 원칙은 도메인을 넘어**. 외고반장 사고 비용이 다른 프로젝트에서 prevention으로 회수되는 통로 — 단순 회고가 아니라 organizational learning asset이 되는 결정적 차이.

---

## 무엇이 달라졌나 — 10개 차이 2줄 압축

### 1. `intent_router_node` (64줄 → 35줄)
LLM 호출/파싱이 base class로 빠져 도메인 의도만 남음.
**비용**: 백틱 hack + json.loads + enum 변환 = 매 호출의 fragile point.

### 2. LLM call abstraction
각 파일이 `ChatOpenAI`를 직접 호출 → chain마다 미묘하게 다른 설정(retry/include_raw/method).
**비용**: 운영 사고 시 어느 chain의 어떤 설정이 문제인지 추적 불가.

### 3. Schema location
`workforce_contract.py` 한 파일에 schema + validator + parser + adapter가 다 섞임.
**비용**: 정책 변경 시 schema도 건드리게 됨, 다른 agent가 schema 재사용 어려움.

### 4. Fake judgment chain (Mission 008~013)
실제 LLM 호출 전에 fake provider로 계약을 먼저 닫는 우회 단계가 한 라운드 들어갔다 정리됨.
**비용**: schema strict + retry로 같은 안전 효과 → day-1에서는 우회 자체가 불필요.

### 5. `langchain_runtime/` 빈 폴더
Mission 012에서 만든 LangChain adapter 폴더가 정리되며 `__pycache__`만 남은 흔적.
**비용**: 새 개발자가 "이게 쓰이나?" 추적하다 시간 낭비, 코드베이스 청결성 저하.

### 6. `rag_hyunwook` / `rag_tayna`
팀원별 폴더 분기 → 거의 동일한 RAG 코드가 두 곳에 중복.
**비용**: 정책 변경 시 두 곳 수정 필요, 한 곳 빠뜨리면 사일런트 불일치.

### 7. Validator 분리
`model_validator(mode="after")` 한 곳에 forbidden phrase + evidence + business rule이 다 박힘.
**비용**: schema 변경이 정책 검증을 깨고, 정책 추가가 schema를 부풀리고, 위반 종류 구분 불가.

### 8. Evidence Log raw text
LLM raw 응답을 어디까지 저장할지 정책이 명확하지 않은 상태 → PII 누출 위험.
**비용**: 외국인등록번호·여권 같은 PII가 감사 로그에 남으면 보안 사고, 후속 정리 비용 큼.

### 9. `pyproject.toml` lock (`>=0.3.0`)
실제 lock은 1.2.17인데 의도가 0.3+로 적힘 → 코드는 1.x 쓰는데 의도는 0.x.
**비용**: lock 갱신 시 0.x로 회귀 가능, 1.0 전용 기능(`with_structured_output` 등) 의도 불명확.

### 10. `runtime_mode`
필요해서 도입 → 정리됐다가 → 다시 도입 (1라운드 왔다갔다).
**비용**: 운영 kill switch + CI 보호 + A/B 인프라 부재로 그동안 LLM 호출 제어 수단 없음.

### 한 줄 패턴 — 3가지 메타 패턴

10개 차이를 종류별로 묶으면:

**1. Abstraction 부재** (#1, #2, #7) — base class·validator 분리 같은 일관 추상화가 없어서 같은 코드가 흩어짐.
**2. 흔적/잔재** (#4, #5, #6, #10) — 진화 과정의 실험이 정리 안 되어 코드베이스에 거짓 신호로 남음.
**3. 의도와 코드 불일치** (#3, #8, #9) — 정책/lock/저장 형태가 명시 안 되어 코드가 임시 결정으로 굳음.

→ **day-1 1.0 설계의 진짜 가치는 이 3 패턴을 처음부터 차단하는 것.** 점진 진화는 부드럽지만 매 단계마다 잔재와 불일치를 만든다는 사실이 10개 차이에서 보임.

---

## 참고

- 코드 reference: `docs/langchain-1-ideal-day1-design.md`
- 현재 마이그레이션 계획: `docs/langchain-1-migration-plan.md`
- 도메인 안전 규칙: `AGENTS.md`, `docs/SECURITY_GUARDRAILS.md`
- LangChain 1.0 학습: https://www.notion.so/0d54b612422382aa96b88165473ff63f
- Notion 5️⃣ LLM 호출 체인: https://www.notion.so/35b4b612422380ec9964fb27162c2b05
