"""메인 오케스트레이터"""

import asyncio
import logging
from typing import Optional

from qfin.core.notifier import Notifier

from .core.filter import CompositeFilter, NewsFilter, PassAllFilter
from .core.source import NewsSource
from .core.types import NewsAlert, NewsItem

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

    async def run(self) -> None:
        """모든 소스 동시 실행"""
        logger.info(f"NewsOrchestrator 시작 ({len(self.sources)}개 소스)")

        await self.notifier.start()

        for source in self.sources:
            await source.connect()

        # 각 소스를 별도 태스크로 실행
        self._tasks = [asyncio.create_task(self._process_source(source)) for source in self.sources]

        try:
            await asyncio.gather(*self._tasks)
        except KeyboardInterrupt:
            logger.info("종료 신호 수신")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """모든 소스 및 알림 종료"""
        logger.info("NewsOrchestrator 종료 중...")

        for task in self._tasks:
            task.cancel()

        for source in self.sources:
            await source.disconnect()

        await self.notifier.stop()

        logger.info("NewsOrchestrator 종료 완료")

    async def _process_source(self, source: NewsSource) -> None:
        """단일 소스 처리

        Args:
            source: 처리할 뉴스 소스
        """
        logger.info(f"[{source.name}] 소스 처리 시작")

        try:
            async for item in source.stream():
                if self.filter.should_pass(item):
                    alert = self._to_alert(item)
                    await self.notifier.send(alert)
                    logger.info(f"[{source.name}] 알림 발송: {item.headline}")
                else:
                    logger.debug(f"[{source.name}] 필터링됨: {item.headline}")
        except asyncio.CancelledError:
            logger.info(f"[{source.name}] 태스크 취소됨")
        except Exception as e:
            logger.error(f"[{source.name}] 처리 에러: {e}", exc_info=True)

    def _to_alert(self, item: NewsItem) -> NewsAlert:
        """NewsItem → NewsAlert 변환

        qfin의 Alert 형식으로 변환하여 DiscordNotifier 호환
        """
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


async def main():
    """진입점"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # TODO: 실제 구현에서는 config에서 로드
    sources: list[NewsSource] = []
    filters: list[NewsFilter] = []

    # TODO: qfin DiscordNotifier 초기화
    # notifier = DiscordNotifier(webhook_url="...")

    # orchestrator = NewsOrchestrator(sources, notifier, filters)
    # await orchestrator.run()

    logger.info("아직 구현되지 않음 (소스 및 필터 추가 필요)")


if __name__ == "__main__":
    asyncio.run(main())
