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
