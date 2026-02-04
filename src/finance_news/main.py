"""메인 오케스트레이터

모든 뉴스 소스를 통합하여 실행하고, 필터링 후 Discord로 알림을 발송합니다.

사용법:
    python -m finance_news.main

환경변수:
    FINANCE_NEWS_FINNHUB_API_KEY: Finnhub API 키
    FINANCE_NEWS_FRED_API_KEY: FRED API 키
    FINANCE_NEWS_DISCORD_WEBHOOK_URL: Discord Webhook URL
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from qfin.core.notifier import Notifier
from qfin.notifiers.discord import DiscordNotifier

from .config import Settings, load_settings
from .core.filter import CompositeFilter, NewsFilter, PassAllFilter
from .core.source import NewsSource
from .core.types import NewsAlert, NewsItem
from .filters import DeduplicationFilter, KeywordFilter
from .sources import FinnhubSource, FREDSource, RSSSource, SECSource

logger = logging.getLogger(__name__)


class NewsOrchestrator:
    """뉴스 수집 오케스트레이터

    여러 뉴스 소스를 동시에 실행하고 필터링 후 알림 발송
    """

    def __init__(
        self,
        sources: list[NewsSource],
        notifier: Notifier,
        filters: Optional[list[NewsFilter]] = None,
    ):
        self.sources = sources
        self.notifier = notifier
        self.filter = CompositeFilter(filters) if filters else PassAllFilter()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def run(self) -> None:
        """모든 소스 동시 실행"""
        logger.info(f"NewsOrchestrator 시작 ({len(self.sources)}개 소스)")
        self._running = True

        await self.notifier.start()

        for source in self.sources:
            await source.connect()

        # 각 소스를 별도 태스크로 실행
        self._tasks = [asyncio.create_task(self._process_source(source)) for source in self.sources]

        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("태스크 취소됨")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """모든 소스 및 알림 종료"""
        if not self._running:
            return

        self._running = False
        logger.info("NewsOrchestrator 종료 중...")

        for task in self._tasks:
            if not task.done():
                task.cancel()

        for source in self.sources:
            try:
                await source.disconnect()
            except Exception as e:
                logger.error(f"소스 종료 에러: {e}")

        try:
            await self.notifier.stop()
        except Exception as e:
            logger.error(f"알림기 종료 에러: {e}")

        logger.info("NewsOrchestrator 종료 완료")

    async def _process_source(self, source: NewsSource) -> None:
        """단일 소스 처리"""
        logger.info(f"[{source.name}] 소스 처리 시작")

        try:
            async for item in source.stream():
                if not self._running:
                    break

                if self.filter.should_pass(item):
                    alert = self._to_alert(item)
                    try:
                        await self.notifier.send(alert)
                        logger.info(f"[{source.name}] 알림 발송: {item.headline[:60]}...")
                    except Exception as e:
                        logger.error(f"[{source.name}] 알림 발송 실패: {e}")
                else:
                    logger.debug(f"[{source.name}] 필터링됨: {item.headline[:60]}...")
        except asyncio.CancelledError:
            logger.info(f"[{source.name}] 태스크 취소됨")
        except Exception as e:
            logger.error(f"[{source.name}] 처리 에러: {e}", exc_info=True)

    def _to_alert(self, item: NewsItem) -> NewsAlert:
        """NewsItem → NewsAlert 변환"""
        return NewsAlert(
            symbol=item.symbols[0] if item.symbols else "MARKET",
            alert_type=f"NEWS_{item.category.value.upper()}",
            message=item.summary or item.headline,
            current_value=0.0,
            change_percent=0.0,
            timestamp=item.published_at,
            headline=item.headline,
            source=item.source,
            url=item.url,
            news_category=item.category.value,
        )


def create_sources(settings: Settings) -> list[NewsSource]:
    """설정 기반으로 소스 생성"""
    sources: list[NewsSource] = []

    # Finnhub (WebSocket)
    if settings.finnhub_api_key:
        sources.append(
            FinnhubSource(
                api_key=settings.finnhub_api_key,
                symbols=settings.finnhub_symbols,
            )
        )
        logger.info(f"Finnhub 소스 추가: {len(settings.finnhub_symbols)}개 심볼")

    # RSS (Polling)
    if settings.rss_feeds:
        sources.append(
            RSSSource(
                feed_urls=settings.rss_feeds,
                interval=settings.rss_poll_interval,
            )
        )
        logger.info(f"RSS 소스 추가: {len(settings.rss_feeds)}개 피드")

    # SEC EDGAR (Polling)
    if settings.sec_ciks:
        sources.append(
            SECSource(
                user_agent=settings.sec_user_agent,
                ciks=settings.sec_ciks,
                form_types=settings.sec_form_types,
                interval=settings.sec_poll_interval,
            )
        )
        logger.info(f"SEC 소스 추가: {len(settings.sec_ciks)}개 회사")

    # FRED (Polling)
    if settings.fred_api_key:
        sources.append(
            FREDSource(
                api_key=settings.fred_api_key,
                series_ids=settings.fred_series_ids,
                interval=settings.fred_poll_interval,
            )
        )
        logger.info(f"FRED 소스 추가: {len(settings.fred_series_ids)}개 지표")

    return sources


def create_filters(settings: Settings) -> list[NewsFilter]:
    """설정 기반으로 필터 생성"""
    filters: list[NewsFilter] = []

    # 중복 제거 필터 (항상 적용)
    filters.append(
        DeduplicationFilter(
            max_cache_size=10000,
            ttl_seconds=86400.0,  # 24시간
        )
    )
    logger.info("중복 제거 필터 추가")

    # 키워드 필터
    if settings.keyword_filters:
        filters.append(
            KeywordFilter(
                include_keywords=settings.keyword_filters,
                use_crypto_preset=True,
                use_market_preset=True,
            )
        )
        logger.info(f"키워드 필터 추가: {len(settings.keyword_filters)}개 키워드")

    return filters


async def main():
    """메인 진입점"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 설정 로드
    try:
        settings = load_settings()
        logger.info(f"설정 로드 완료 (로그 레벨: {settings.log_level})")
    except Exception as e:
        logger.error(f"설정 로드 실패: {e}")
        logger.error(
            "필요한 환경변수: FINANCE_NEWS_FINNHUB_API_KEY, FINANCE_NEWS_FRED_API_KEY, FINANCE_NEWS_DISCORD_WEBHOOK_URL"
        )
        sys.exit(1)

    # 로그 레벨 설정
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

    # 소스 생성
    sources = create_sources(settings)
    if not sources:
        logger.error("활성화된 소스가 없습니다.")
        sys.exit(1)

    # 필터 생성
    filters = create_filters(settings)

    # Discord 알림기 생성
    notifier = DiscordNotifier(webhook_url=settings.discord_webhook_url)

    # 오케스트레이터 생성
    orchestrator = NewsOrchestrator(
        sources=sources,
        notifier=notifier,
        filters=filters,
    )

    # 시그널 핸들러 설정
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("종료 신호 수신, 종료 중...")
        asyncio.create_task(orchestrator.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # 실행
    logger.info("=" * 60)
    logger.info("Finance News 오케스트레이터 시작")
    logger.info(f"소스: {len(sources)}개, 필터: {len(filters)}개")
    logger.info("=" * 60)

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트")
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
