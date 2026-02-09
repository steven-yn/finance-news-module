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
import sqlite3
import sys
from typing import Optional

from finance_notifier import DiscordNotifier
from finance_notifier.adapters.finance_news import news_item_to_message
from finance_notifier.core.notifier import Notifier

from .config import Settings, load_settings
from .core.filter import CompositeFilter, NewsFilter, PassAllFilter
from .core.source import NewsSource
from .core.types import NewsItem
from .db import NewsRepository, init_db
from .filters import KeywordFilter
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
        repository: NewsRepository,
        filters: Optional[list[NewsFilter]] = None,
    ):
        self.sources = sources
        self.notifier = notifier
        self.repository = repository
        self.filters = filters or []
        self.filter = CompositeFilter(filters) if filters else PassAllFilter()
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._input_task: Optional[asyncio.Task] = None

    async def run(self) -> None:
        """모든 소스 동시 실행"""
        logger.info(f"NewsOrchestrator 시작 ({len(self.sources)}개 소스)")
        self._running = True

        await self.notifier.start()

        for source in self.sources:
            await source.connect()

        # 각 소스를 별도 태스크로 실행
        self._tasks = [asyncio.create_task(self._process_source(source)) for source in self.sources]

        # 키보드 입력 처리 태스크
        self._input_task = asyncio.create_task(self._handle_input())

        try:
            await asyncio.gather(*self._tasks, self._input_task)
        except asyncio.CancelledError:
            logger.info("태스크 취소됨")
        finally:
            await self.stop()

    def refresh(self) -> None:
        """모든 소스 수동 새로고침"""
        logger.info("=" * 40)
        logger.info("수동 새로고침 실행")
        logger.info("=" * 40)
        for source in self.sources:
            if hasattr(source, "trigger_refresh"):
                source.trigger_refresh()

    async def _handle_input(self) -> None:
        """키보드 입력 처리 (r: 새로고침, s: 통계, q: 종료)"""
        print("\n" + "=" * 50)
        print("명령어: [r] 새로고침 | [s] 통계 | [q] 종료")
        print("=" * 50 + "\n")

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while self._running:
            try:
                line = await reader.readline()
                if not line:
                    break

                cmd = line.decode().strip().lower()
                if cmd == "r":
                    self.refresh()
                elif cmd == "s":
                    self._print_stats()
                elif cmd == "q":
                    logger.info("종료 명령 수신")
                    await self.stop()
                    break
                elif cmd == "h" or cmd == "help":
                    print("\n명령어: [r] 새로고침 | [s] 통계 | [q] 종료\n")
            except Exception as e:
                logger.debug(f"입력 처리 에러: {e}")
                break

    def _print_stats(self) -> None:
        """DB 통계 출력"""
        stats = self.repository.get_stats()
        print("\n" + "=" * 50)
        print(f"총 뉴스: {stats['total']}개 | 알림 발송: {stats['notified']}개")
        print("-" * 50)
        print("소스별:")
        for source, count in stats["by_source"].items():
            print(f"  {source}: {count}개")
        print("-" * 50)
        print("카테고리별:")
        for category, count in stats["by_category"].items():
            print(f"  {category}: {count}개")
        print("=" * 50 + "\n")

    async def stop(self) -> None:
        """모든 소스 및 알림 종료"""
        if not self._running:
            return

        self._running = False
        logger.info("NewsOrchestrator 종료 중...")

        # 입력 태스크 취소
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()

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

                # DB 중복 체크 (이미 저장된 뉴스는 스킵)
                if self.repository.exists(item):
                    logger.debug(f"[{source.name}] 중복 뉴스: {item.headline[:50]}...")
                    continue

                # 키워드 필터 적용
                if not self.filter.should_pass(item):
                    # 필터링된 뉴스도 DB에 저장 (알림 미발송)
                    self.repository.save(item, notified=False)
                    logger.debug(f"[{source.name}] 필터링됨: {item.headline[:50]}...")
                    continue

                # 알림 발송
                message = news_item_to_message(item)
                try:
                    await self.notifier.send(message)
                    # 발송 성공 시 DB 저장 (알림 발송 표시)
                    self.repository.save(item, notified=True)
                    logger.info(f"[{source.name}] 알림 발송: {item.headline[:60]}...")
                except Exception as e:
                    # 발송 실패해도 DB에 저장 (재시도 방지)
                    self.repository.save(item, notified=False)
                    logger.error(f"[{source.name}] 알림 발송 실패: {e}")

        except asyncio.CancelledError:
            logger.info(f"[{source.name}] 태스크 취소됨")
        except Exception as e:
            logger.error(f"[{source.name}] 처리 에러: {e}", exc_info=True)


def create_sources(settings: Settings) -> list[NewsSource]:
    """설정 기반으로 소스 생성"""
    sources: list[NewsSource] = []

    # Finnhub (REST API Polling)
    if settings.finnhub_api_key:
        sources.append(
            FinnhubSource(
                api_key=settings.finnhub_api_key,
                categories=settings.finnhub_categories,
                interval=settings.finnhub_poll_interval,
            )
        )
        logger.info(f"Finnhub 소스 추가: {', '.join(settings.finnhub_categories)} 카테고리")

    # RSS (Polling)
    if settings.rss_feeds:
        sources.append(
            RSSSource(
                feed_urls=settings.rss_feeds,
                interval=settings.rss_poll_interval,
            )
        )
        logger.info(f"RSS 소스 추가: {len(settings.rss_feeds)}개 피드")

    # SEC EDGAR (Polling) - 개별 기업 공시 수집 비활성화
    # SEC 소스는 현재 비활성화 상태 (개별 기업 공시 제거됨)
    # if settings.sec_user_agent:
    #     sources.append(
    #         SECSource(
    #             user_agent=settings.sec_user_agent,
    #             form_types=settings.sec_form_types,
    #             interval=settings.sec_poll_interval,
    #         )
    #     )
    #     logger.info("SEC 소스 추가 (개별 기업 공시 비활성화)")

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

    # 키워드 필터 (중복 제거는 DB에서 처리)
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

    # 데이터베이스 초기화
    conn = init_db(settings.db_path)
    repository = NewsRepository(conn)
    logger.info(f"데이터베이스 연결 완료: {settings.db_path}")

    # 오래된 뉴스 정리
    deleted = repository.delete_old(settings.db_retention_days)
    if deleted > 0:
        logger.info(f"{settings.db_retention_days}일 이전 뉴스 {deleted}개 삭제")

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
        repository=repository,
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
    stats = repository.get_stats()
    logger.info(f"DB 저장 뉴스: {stats['total']}개")
    logger.info("=" * 60)

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트")
    finally:
        await orchestrator.stop()
        conn.close()
        logger.info("데이터베이스 연결 종료")


if __name__ == "__main__":
    asyncio.run(main())
