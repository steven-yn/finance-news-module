"""설정 관리 (pydantic-settings 기반)"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FINANCE_NEWS_",
        extra="ignore",
    )

    # API Keys
    finnhub_api_key: str = Field(..., description="Finnhub API 키")
    fred_api_key: str = Field(..., description="FRED API 키")
    discord_webhook_url: str = Field(..., description="Discord Webhook URL")

    # Finnhub Settings
    finnhub_symbols: list[str] = Field(
        default=["CRYPTO:BTC", "CRYPTO:ETH", "CRYPTO:SOL", "CRYPTO:XRP"],
        description="구독할 암호화폐 심볼",
    )

    # RSS Settings
    rss_feeds: list[str] = Field(
        default=[
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
            "https://www.cnbc.com/id/33002080/device/rss/rss.html",  # CNBC Crypto
        ],
        description="RSS 피드 URL 목록",
    )
    rss_poll_interval: float = Field(default=120.0, description="RSS 폴링 간격 (초)")

    # SEC Settings
    sec_poll_interval: float = Field(default=60.0, description="SEC 폴링 간격 (초)")

    # FRED Settings
    fred_series_ids: list[str] = Field(
        default=["DFF", "CPIAUCSL", "UNRATE"],  # 연방기금금리, CPI, 실업률
        description="모니터링할 FRED 시리즈 ID",
    )
    fred_poll_interval: float = Field(default=300.0, description="FRED 폴링 간격 (초)")

    # Filter Settings
    keyword_filters: list[str] = Field(
        default=["bitcoin", "crypto", "ethereum", "blockchain", "btc", "eth"],
        description="뉴스 필터링 키워드",
    )

    # Logging
    log_level: str = Field(default="INFO", description="로그 레벨")


def load_settings() -> Settings:
    """설정 로드"""
    return Settings()
