from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_AUTH_PEPPER = "local-dev-insecure-pepper-change-me"


class Settings(BaseSettings):
    """DATABASE_URL 등 런타임 설정. 서비스 DB는 PostgreSQL 16+로 확정(docs/DB_SCHEMA.md §1)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
    environment: str = "local"
    auth_pepper: str = INSECURE_DEFAULT_AUTH_PEPPER  # OTP/세션 토큰 해시 pepper — 배포 전 반드시 env로 교체
    rag_service_url: str = "http://localhost:8100"  # rag 서비스(내부 전용, plans/BACKEND_CONNECT.md 토폴로지)
    rag_service_timeout_seconds: float = 30.0
    # R2.1 — 프론트(src/lib/api/)가 실서버 모드(VITE_API_MODE=real)에서 이 origin으로 호출한다.
    # 로컬 Vite 기본 포트(5173)만 기본 허용 — 배포 시 실제 프론트 origin으로 교체한다.
    cors_allow_origins: list[str] = ["http://localhost:5173"]
    # R5.4 — 실 FCM/APNs 자격증명. `app/api/v1/auth.py`의 `debug_code=... if is_local else None`
    # 게이트와 동일한 원칙: 이 값이 없으면(이 저장소·CI·리뷰어 환경 전부 기본값) push_adapter가
    # 로그 전용 no-op으로만 동작한다 — placeholder 값으로 실 외부 호출을 시도하지 않는다.
    push_provider_credentials: str | None = None

    # R3 — 메시징 채널 어댑터 자격 증명(backend/app/services/channels/). 전부 기본값 None —
    # 이 dev 환경·CI·리뷰어 환경엔 실계정이 없으므로 항상 비어 있다. auth.py의
    # `debug_code=code if get_settings().is_local else None`과 동일한 원칙: 어댑터는 아래 값이
    # 하나라도 비면 실 HTTP 호출을 절대 만들지 않고 스텁으로 처리한다(services/channels/*.py).
    solapi_api_key: str | None = None
    solapi_api_secret: str | None = None
    solapi_sender: str | None = None  # 발신 번호(사전 등록된 발신번호만 허용하는 SMS 게이트웨이 공통 제약)
    kakao_alimtalk_sender_key: str | None = None  # 카카오 비즈메시지 발신 프로필 키(플러스친구)
    kakao_alimtalk_template_code: str | None = None  # 사전 심사된 알림톡 템플릿 코드
    zalo_oa_access_token: str | None = None
    zalo_oa_id: str | None = None
    zalo_webhook_secret: str | None = None  # 미설정이면 인바운드 webhook은 503(§1 원칙을 인바운드에도 동일 적용)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    smtp_from: str | None = None

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @model_validator(mode="after")
    def _forbid_insecure_pepper_outside_local(self) -> "Settings":
        """어드버서리얼 보안 리뷰 F2/F8: environment가 local이 아닌데 기본 pepper가 그대로면
        fail-open이다(디버그 OTP 코드 노출은 없어지지만, 알려진 문자열로 HMAC pepper가 뚫린
        채 배포될 수 있음). 기동 시점에 강제 차단한다 — 조용히 넘어가지 않는다."""
        if not self.is_local and self.auth_pepper == INSECURE_DEFAULT_AUTH_PEPPER:
            raise ValueError(
                "AUTH_PEPPER must be set via environment when ENVIRONMENT != 'local' "
                "(refusing to start with the insecure local-dev default pepper)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
