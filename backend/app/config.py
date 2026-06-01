"""애플리케이션 설정 — .env에서 로드."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트(.env 위치): backend/app/config.py → 상위 2단계
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Naver OpenAPI
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # 한국은행 ECOS (환율)
    ecos_api_key: str = ""

    # DB
    database_url: str = "postgresql+psycopg://price:price_pw@localhost:5432/price_dashboard"

    # 수집/집계
    anomaly_threshold_pct: float = 10.0
    collect_display: int = 50


settings = Settings()
