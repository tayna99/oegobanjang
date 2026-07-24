"""채널 어댑터 자격 증명 게이팅 — CLAUDE.md 태스크의 "가장 중요한 가드레일":
자격 증명 미설정 시 실 외부 HTTP 호출이 절대 발생하지 않는다(respx가 미모킹 요청에 예외를
던지므로, 이 테스트들은 그 자체로 "0건의 실 호출"을 구조적으로 증명한다).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.config import get_settings
from app.services.channels.alimtalk import AlimtalkAdapter
from app.services.channels.email import EmailAdapter
from app.services.channels.sms import SmsAdapter
from app.services.channels.zalo import ZaloAdapter


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- 자격 증명 미설정 → 스텁, 실 HTTP 호출 0건 ------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_sms_adapter_stubs_when_credentials_unset(monkeypatch) -> None:
    monkeypatch.delenv("SOLAPI_API_KEY", raising=False)
    monkeypatch.delenv("SOLAPI_API_SECRET", raising=False)
    monkeypatch.delenv("SOLAPI_SENDER", raising=False)
    get_settings.cache_clear()

    result = await SmsAdapter().send(to="010-0000-0000", body="test")

    assert result.status == "sent"
    assert result.is_stub is True
    assert result.external_id is not None and result.external_id.startswith("stub:sms:")
    # respx.mock 안에서 아무 라우트도 등록하지 않았다 — 미모킹 요청이 있었다면 respx가
    # AssertionError(또는 연결 실패)를 던졌을 것이므로, 정상 종료 자체가 "실 호출 0건"의 증거다.
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_alimtalk_adapter_stubs_when_template_unset(monkeypatch) -> None:
    # SMS 자격 증명만 있고 알림톡 전용 템플릿이 없는 흔한 경우도 스텁이어야 한다.
    monkeypatch.setenv("SOLAPI_API_KEY", "key")
    monkeypatch.setenv("SOLAPI_API_SECRET", "secret")
    monkeypatch.setenv("SOLAPI_SENDER", "01000000000")
    monkeypatch.delenv("KAKAO_ALIMTALK_SENDER_KEY", raising=False)
    monkeypatch.delenv("KAKAO_ALIMTALK_TEMPLATE_CODE", raising=False)
    get_settings.cache_clear()

    result = await AlimtalkAdapter().send(to="010-0000-0000", body="test")

    assert result.status == "sent"
    assert result.is_stub is True
    assert result.external_id is not None and result.external_id.startswith("stub:alimtalk:")
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_zalo_adapter_stubs_when_credentials_unset(monkeypatch) -> None:
    monkeypatch.delenv("ZALO_OA_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()

    result = await ZaloAdapter().send(to="zalo-user-1", body="test")

    assert result.status == "sent"
    assert result.is_stub is True
    assert result.external_id is not None and result.external_id.startswith("stub:zalo:")
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_email_adapter_stubs_when_smtp_unset(monkeypatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    get_settings.cache_clear()

    result = await EmailAdapter().send(to="expert@example.com", body="test")

    assert result.status == "sent"
    assert result.is_stub is True
    assert result.external_id is not None and result.external_id.startswith("stub:email:")


# --- 자격 증명 설정 → 실 요청 형태를 respx로만 검증(실계정에 닿지 않는다) --------------------


@pytest.mark.asyncio
@respx.mock
async def test_sms_adapter_sends_real_request_shape_when_credentials_set(monkeypatch) -> None:
    monkeypatch.setenv("SOLAPI_API_KEY", "key-abc")
    monkeypatch.setenv("SOLAPI_API_SECRET", "secret-xyz")
    monkeypatch.setenv("SOLAPI_SENDER", "01099998888")
    get_settings.cache_clear()

    route = respx.post("https://api.solapi.com/messages/v4/send").mock(
        return_value=httpx.Response(200, json={"messageId": "M123"})
    )

    result = await SmsAdapter().send(to="01011112222", body="안내 문자입니다")

    assert route.called
    request = route.calls.last.request
    assert "HMAC-SHA256" in request.headers["Authorization"]
    assert "apiKey=key-abc" in request.headers["Authorization"]
    import json as _json

    body = _json.loads(request.content)
    assert body["message"]["to"] == "01011112222"
    assert body["message"]["from"] == "01099998888"
    assert body["message"]["text"] == "안내 문자입니다"
    assert result.status == "sent"
    assert result.is_stub is False
    assert result.external_id == "M123"


@pytest.mark.asyncio
@respx.mock
async def test_sms_adapter_reports_failure_on_non_2xx(monkeypatch) -> None:
    monkeypatch.setenv("SOLAPI_API_KEY", "key-abc")
    monkeypatch.setenv("SOLAPI_API_SECRET", "secret-xyz")
    monkeypatch.setenv("SOLAPI_SENDER", "01099998888")
    get_settings.cache_clear()

    respx.post("https://api.solapi.com/messages/v4/send").mock(return_value=httpx.Response(400, text="bad request"))

    result = await SmsAdapter().send(to="01011112222", body="test")

    assert result.status == "failed"
    assert result.external_id is None


@pytest.mark.asyncio
@respx.mock
async def test_alimtalk_adapter_sends_real_request_shape_when_fully_configured(monkeypatch) -> None:
    monkeypatch.setenv("SOLAPI_API_KEY", "key-abc")
    monkeypatch.setenv("SOLAPI_API_SECRET", "secret-xyz")
    monkeypatch.setenv("SOLAPI_SENDER", "01099998888")
    monkeypatch.setenv("KAKAO_ALIMTALK_SENDER_KEY", "pf-123")
    monkeypatch.setenv("KAKAO_ALIMTALK_TEMPLATE_CODE", "tpl-456")
    get_settings.cache_clear()

    route = respx.post("https://api.solapi.com/messages/v4/send").mock(
        return_value=httpx.Response(200, json={"messageId": "A999"})
    )

    result = await AlimtalkAdapter().send(to="01011112222", body="서류 요청 안내")

    assert route.called
    import json as _json

    body = _json.loads(route.calls.last.request.content)
    assert body["message"]["type"] == "ATA"
    assert body["message"]["kakaoOptions"] == {"pfId": "pf-123", "templateId": "tpl-456"}
    assert result.status == "sent"
    assert result.external_id == "A999"


@pytest.mark.asyncio
@respx.mock
async def test_zalo_adapter_sends_real_request_shape_when_token_set(monkeypatch) -> None:
    monkeypatch.setenv("ZALO_OA_ACCESS_TOKEN", "token-abc")
    get_settings.cache_clear()

    route = respx.post("https://openapi.zalo.me/v3.0/oa/message/cs").mock(
        return_value=httpx.Response(200, json={"error": 0, "message": "Success", "data": {"message_id": "Z1"}})
    )

    result = await ZaloAdapter().send(to="zalo-user-1", body="안내 메시지")

    assert route.called
    request = route.calls.last.request
    assert request.headers["access_token"] == "token-abc"
    import json as _json

    body = _json.loads(request.content)
    assert body["recipient"]["user_id"] == "zalo-user-1"
    assert result.status == "sent"
    assert result.external_id == "Z1"


@pytest.mark.asyncio
@respx.mock
async def test_zalo_adapter_reports_failure_on_logical_error_envelope(monkeypatch) -> None:
    monkeypatch.setenv("ZALO_OA_ACCESS_TOKEN", "token-abc")
    get_settings.cache_clear()

    respx.post("https://openapi.zalo.me/v3.0/oa/message/cs").mock(
        return_value=httpx.Response(200, json={"error": -216, "message": "Invalid user_id"})
    )

    result = await ZaloAdapter().send(to="bad-user", body="test")

    assert result.status == "failed"
    assert result.external_id is None


# EmailAdapter는 httpx가 아니라 smtplib(동기)를 쓴다 — respx로는 목킹할 수 없으므로 SMTP
# 클래스 자체를 목으로 바꿔 실 서버 연결 없이 요청 형태(로그인·발신자·수신자·본문)만 검증한다.
@pytest.mark.asyncio
async def test_email_adapter_sends_via_smtp_when_credentials_set(monkeypatch) -> None:
    import smtplib as smtplib_module
    from unittest.mock import MagicMock

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "outbox@example.com")
    monkeypatch.setenv("SMTP_PASS", "app-password")
    monkeypatch.setenv("SMTP_FROM", "외고반장 <outbox@example.com>")
    get_settings.cache_clear()

    mock_smtp_instance = MagicMock()
    mock_smtp_context = MagicMock()
    mock_smtp_context.__enter__.return_value = mock_smtp_instance
    mock_smtp_ctor = MagicMock(return_value=mock_smtp_context)
    monkeypatch.setattr(smtplib_module, "SMTP", mock_smtp_ctor)

    result = await EmailAdapter().send(to="expert@lawfirm.example", body="패키지 링크 안내", subject="검토 요청")

    mock_smtp_ctor.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("outbox@example.com", "app-password")
    mock_smtp_instance.send_message.assert_called_once()
    sent_message = mock_smtp_instance.send_message.call_args[0][0]
    assert sent_message["To"] == "expert@lawfirm.example"
    assert sent_message["Subject"] == "검토 요청"
    assert result.status == "sent"
    assert result.is_stub is False


@pytest.mark.asyncio
async def test_email_adapter_reports_failure_on_smtp_error(monkeypatch) -> None:
    import smtplib as smtplib_module
    from unittest.mock import MagicMock

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "outbox@example.com")
    monkeypatch.setenv("SMTP_PASS", "wrong-password")
    monkeypatch.setenv("SMTP_FROM", "outbox@example.com")
    get_settings.cache_clear()

    mock_smtp_ctor = MagicMock(side_effect=smtplib_module.SMTPAuthenticationError(535, b"bad credentials"))
    monkeypatch.setattr(smtplib_module, "SMTP", mock_smtp_ctor)

    result = await EmailAdapter().send(to="expert@lawfirm.example", body="test")

    assert result.status == "failed"
    assert result.external_id is None
