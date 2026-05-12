from __future__ import annotations

import json
import os
from typing import Any, Protocol

from backend.app.agent_runtime.translation.schemas import (
    TranslationRequest,
    TranslationResult,
)


DEFAULT_TRANSLATION_MODEL = "gpt-4.1-nano"
DEFAULT_TRANSLATION_TIMEOUT_SECONDS = 20.0
DEFAULT_TRANSLATION_MAX_RETRIES = 2
LLM_UNAVAILABLE_FLAG = "LLM_TRANSLATION_UNAVAILABLE"
LLM_FAILED_FLAG = "LLM_TRANSLATION_FAILED"
RULE_BASED_FALLBACK_PROVIDER = "rule_based_fallback"


class TranslationProvider(Protocol):
    def translate(self, request: TranslationRequest) -> TranslationResult:
        ...


class RuleBasedTranslationProvider:
    provider_name = "rule_based"

    def translate(self, request: TranslationRequest) -> TranslationResult:
        if request.source_language == request.target_language:
            return TranslationResult(
                translated_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                provider=self.provider_name,
            )

        if request.target_language == "ko":
            return _translate_to_ko(request)

        return TranslationResult(
            translated_text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            risk_flags=["TRANSLATION_REVIEW_REQUIRED"],
            review_required=True,
            provider=self.provider_name,
        )


class MockTranslationProvider:
    provider_name = "mock"

    def __init__(
        self,
        translations: dict[tuple[str, str, str], str] | None = None,
    ) -> None:
        self.translations = translations or {}

    def translate(self, request: TranslationRequest) -> TranslationResult:
        translated = self.translations.get(
            (
                request.source_language,
                request.target_language,
                request.text,
            )
        )
        if translated is None:
            translated = f"[mock:{request.source_language}->{request.target_language}] {request.text}"

        return TranslationResult(
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
            provider=self.provider_name,
        )


class LLMTranslationProvider:
    provider_name = "llm"

    def __init__(
        self,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        fallback_provider: TranslationProvider | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or os.getenv("TRANSLATION_MODEL") or DEFAULT_TRANSLATION_MODEL
        self.timeout_seconds = _env_float(
            "TRANSLATION_TIMEOUT_SECONDS",
            timeout_seconds,
            DEFAULT_TRANSLATION_TIMEOUT_SECONDS,
        )
        self.max_retries = _env_int(
            "TRANSLATION_MAX_RETRIES",
            max_retries,
            DEFAULT_TRANSLATION_MAX_RETRIES,
        )
        self.fallback_provider = fallback_provider or RuleBasedTranslationProvider()
        self.client = client
        self.api_key = os.getenv("OPENAI_API_KEY")

    def translate(self, request: TranslationRequest) -> TranslationResult:
        if not self.api_key:
            return self._fallback(
                request,
                risk_flag=LLM_UNAVAILABLE_FLAG,
            )

        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                payload = self._call_llm(request)
                return self._parse_payload(request, payload)
            except Exception as exc:  # noqa: BLE001 - all LLM failures fall back safely.
                last_error = exc

        return self._fallback(
            request,
            risk_flag=LLM_FAILED_FLAG,
            error=last_error,
        )

    def _call_llm(self, request: TranslationRequest) -> dict[str, Any]:
        client = self.client or self._build_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": _system_prompt(),
                },
                {
                    "role": "user",
                    "content": _user_prompt(request),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
            timeout=self.timeout_seconds,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty content")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be a JSON object")
        return parsed

    def _build_client(self) -> Any:
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=0,
        )

    def _parse_payload(
        self,
        request: TranslationRequest,
        payload: dict[str, Any],
    ) -> TranslationResult:
        translated_text = str(payload.get("translated_text") or "").strip()
        if not translated_text:
            raise ValueError("LLM response missing translated_text")

        return TranslationResult(
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            risk_flags=_dedupe(_as_str_list(payload.get("risk_flags"))),
            review_required=True,
            provider=self.provider_name,
        )

    def _fallback(
        self,
        request: TranslationRequest,
        *,
        risk_flag: str,
        error: Exception | None = None,
    ) -> TranslationResult:
        fallback = self.fallback_provider.translate(request)
        risk_flags = _dedupe(fallback.risk_flags + [risk_flag])
        if error is not None:
            risk_flags = _dedupe(risk_flags + [LLM_FAILED_FLAG])
        return TranslationResult(
            translated_text=fallback.translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            risk_flags=risk_flags,
            review_required=True,
            provider=RULE_BASED_FALLBACK_PROVIDER,
        )


def translate_text(
    *,
    text: str,
    source_language: str,
    target_language: str,
    purpose: str | None = None,
    provider: TranslationProvider | None = None,
) -> TranslationResult:
    translator = provider or RuleBasedTranslationProvider()
    request = TranslationRequest(
        text=text,
        source_language=source_language,
        target_language=target_language,
        purpose=purpose,
    )
    return translator.translate(request)


def _translate_to_ko(request: TranslationRequest) -> TranslationResult:
    normalized = request.text.lower()
    fragments: list[str] = []

    if _contains_any(normalized, ("hộ chiếu", "passport", "paspor", "여권")):
        fragments.append("여권은 보유한 것으로 보입니다")
    if _contains_any(normalized, ("ảnh", "photo", "foto", "사진")):
        fragments.append("사진 제출 상태 확인이 필요합니다")
    if _contains_any(normalized, ("ngày mai", "besok", "tomorrow", "내일")):
        fragments.append("내일 제출 가능하다는 의미가 포함되어 있습니다")
    if _contains_any(
        normalized,
        ("không thể", "belum", "belum bisa", "can't", "cannot", "못"),
    ):
        fragments.append("제출 지연 또는 준비 어려움 가능성이 있습니다")
    if _contains_any(normalized, ("gọi", "call", "hubungi", "전화")):
        fragments.append("전화 또는 연락 요청 가능성이 있습니다")
    if _contains_any(normalized, ("asrama", "housing", "ký túc xá", "기숙사")):
        fragments.append("기숙사 또는 주거 관련 확인이 필요할 수 있습니다")
    if _contains_any(normalized, ("counseling", "konseling", "tư vấn", "상담")):
        fragments.append("상담 지원이 필요할 수 있습니다")

    if not fragments:
        return TranslationResult(
            translated_text=f"번역 검토 필요: {request.text}",
            source_language=request.source_language,
            target_language=request.target_language,
            risk_flags=["TRANSLATION_REVIEW_REQUIRED"],
            review_required=True,
            provider="rule_based",
        )

    return TranslationResult(
        translated_text="; ".join(fragments) + ".",
        source_language=request.source_language,
        target_language=request.target_language,
        risk_flags=["TRANSLATION_REVIEW_REQUIRED"],
        review_required=True,
        provider="rule_based",
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _system_prompt() -> str:
    return "\n".join(
        [
            "You are a translation component for an internal foreign hiring operations system.",
            "You do not decide visa eligibility.",
            "You do not provide legal/labor advice.",
            "You do not send messages.",
            "You only translate or summarize.",
            "Return JSON only.",
            "Do not add coercive, discriminatory, legal, or final-status language.",
        ]
    )


def _user_prompt(request: TranslationRequest) -> str:
    return json.dumps(
        {
            "task": "translate_text",
            "source_language": request.source_language,
            "target_language": request.target_language,
            "purpose": request.purpose,
            "text": request.text,
            "required_response_schema": {
                "translated_text": "string",
                "risk_flags": ["string"],
                "review_required": True,
            },
            "safety_constraints": [
                "Do not decide visa eligibility.",
                "Do not provide legal or labor advice.",
                "Do not claim any message was sent.",
                "Return a translation draft requiring human review.",
            ],
        },
        ensure_ascii=False,
    )


def _env_float(name: str, explicit: float | None, default: float) -> float:
    if explicit is not None:
        return explicit
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, explicit: int | None, default: int) -> int:
    if explicit is not None:
        return explicit
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
