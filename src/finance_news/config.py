"""설정 관리 (pydantic-settings 기반)"""

from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FINANCE_NEWS_",
        extra="ignore",
    )

    # API Keys (선택적 - 최소 하나 이상 필요)
    finnhub_api_key: Optional[str] = Field(default=None, description="Finnhub API 키")
    fred_api_key: Optional[str] = Field(default=None, description="FRED API 키")
    discord_webhook_url: str = Field(..., description="Discord Webhook URL")

    @field_validator("discord_webhook_url")
    @classmethod
    def validate_discord_webhook(cls, v: str) -> str:
        """Discord Webhook URL 검증"""
        if not v or not v.strip():
            raise ValueError("Discord Webhook URL은 필수입니다")
        valid_prefixes = (
            "https://discord.com/api/webhooks/",
            "https://discordapp.com/api/webhooks/",
        )
        if not v.startswith(valid_prefixes):
            raise ValueError("유효한 Discord Webhook URL이 아닙니다")
        return v.strip()

    @field_validator("finnhub_api_key", "fred_api_key", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Optional[str]) -> Optional[str]:
        """빈 문자열을 None으로 변환"""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_at_least_one_source(self) -> "Settings":
        """최소 하나 이상의 뉴스 소스가 활성화되어야 함"""
        has_finnhub = bool(self.finnhub_api_key)
        has_fred = bool(self.fred_api_key)
        has_rss = len(self.rss_feeds) > 0
        has_sec = len(self.sec_ciks) > 0

        if not any([has_finnhub, has_fred, has_rss, has_sec]):
            raise ValueError(
                "최소 하나 이상의 뉴스 소스가 필요합니다. "
                "finnhub_api_key, fred_api_key, rss_feeds, sec_ciks 중 하나 이상 설정하세요."
            )
        return self

    # Finnhub Settings (REST API Polling)
    finnhub_categories: list[str] = Field(
        default=["general", "crypto"],
        description="뉴스 카테고리 (general, crypto, forex, merger)",
    )
    finnhub_poll_interval: float = Field(default=60.0, description="Finnhub 폴링 간격 (초)")

    # RSS Settings
    rss_feeds: list[str] = Field(
        default=[
            # 주요 금융 언론
            "https://feeds.bloomberg.com/markets/news.rss",  # Bloomberg Markets
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # Wall Street Journal Markets
            "https://www.ft.com/rss/home/uk",  # Financial Times
            "https://ir.thomsonreuters.com/rss/news-releases.xml?items=15",  # Thomson Reuters News
            # 암호화폐 전문
            "https://cointelegraph.com/rss",  # Cointelegraph Crypto
            # 추가 금융 뉴스
            "https://www.investing.com/rss/news.rss",  # Investing.com
            "https://seekingalpha.com/feed.xml",  # Seeking Alpha
        ],
        description="RSS 피드 URL 목록",
    )
    rss_poll_interval: float = Field(default=60.0, description="RSS 폴링 간격 (초)")

    # SEC Settings
    sec_user_agent: str = Field(
        default="FinanceNews/1.0 admin@example.com",
        description="SEC API User-Agent (이메일 포함 필수)",
    )
    sec_ciks: list[str] = Field(
        default=[
            "0000320193",  # Apple
            "0001018724",  # Amazon
            "0001652044",  # Google
            "0001318605",  # Tesla
        ],
        description="모니터링할 회사 CIK 목록",
    )
    sec_form_types: list[str] = Field(
        default=["8-K", "10-K", "10-Q"],
        description="모니터링할 SEC 공시 유형",
    )
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
    dedup_cache_file: str = Field(
        default=".cache/news_dedup.json",
        description="중복 제거 캐시 파일 경로",
    )
    dedup_save_interval: int = Field(
        default=10,
        description="캐시 저장 간격 (N개 뉴스마다 저장)",
    )

    # Logging
    log_level: str = Field(default="INFO", description="로그 레벨")


def load_settings() -> Settings:
    """설정 로드"""
    return Settings()
