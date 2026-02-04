"""뉴스 소스 추상 클래스 및 베이스 구현체"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .types import NewsItem

logger = logging.getLogger(__name__)


class NewsSource(ABC):
    """뉴스 소스 추상 클래스

    qfin의 DataSource와 동일한 인터페이스 패턴을 따름:
    - connect(): 연결/초기화
    - disconnect(): 연결 해제/정리
    - stream(): 데이터 스트림 (AsyncIterator)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """소스 이름"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """연결/초기화"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """연결 해제/정리"""
        pass

    @abstractmethod
    def stream(self) -> AsyncIterator[NewsItem]:
        """뉴스 스트림

        WebSocket: 실시간 수신
        Polling: 내부에서 sleep 처리
        """
        pass


class WebSocketNewsSource(NewsSource):
    """WebSocket 기반 소스 베이스 클래스

    재사용 가능한 WebSocket 연결 관리 로직 제공:
    - 자동 재연결 (지수 백오프)
    - 연결 상태 관리
    - 에러 핸들링
    """

    MAX_RETRIES = 10
    BASE_DELAY = 1.0

    def __init__(self, url: str):
        self.url = url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False

    async def connect(self) -> None:
        """연결 시작"""
        self._running = True
        logger.info(f"[{self.name}] WebSocket 연결 시작: {self.url}")

    async def disconnect(self) -> None:
        """연결 종료"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info(f"[{self.name}] WebSocket 연결 종료")

    @abstractmethod
    async def _parse_message(self, data: dict) -> NewsItem | None:
        """메시지 파싱 (구현체에서 정의)

        Args:
            data: WebSocket에서 받은 JSON 데이터

        Returns:
            NewsItem 또는 None (파싱 실패 시)
        """
        pass

    async def stream(self) -> AsyncIterator[NewsItem]:
        """재연결 로직 포함 스트림"""
        retries = 0

        while self._running and retries < self.MAX_RETRIES:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    retries = 0
                    logger.info(f"[{self.name}] WebSocket 연결 성공")

                    async for message in ws:
                        if not self._running:
                            break

                        try:
                            data = json.loads(message)
                            item = await self._parse_message(data)
                            if item:
                                yield item
                        except json.JSONDecodeError as e:
                            logger.error(f"[{self.name}] JSON 파싱 실패: {e}")
                        except Exception as e:
                            logger.error(f"[{self.name}] 메시지 처리 실패: {e}")

            except ConnectionClosed:
                retries += 1
                delay = min(self.BASE_DELAY * (2**retries), 60)
                logger.warning(
                    f"[{self.name}] 연결 끊김. {delay}초 후 재연결 시도 ({retries}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                retries += 1
                delay = min(self.BASE_DELAY * (2**retries), 60)
                logger.error(f"[{self.name}] 연결 에러: {e}. {delay}초 후 재시도")
                await asyncio.sleep(delay)

        if retries >= self.MAX_RETRIES:
            logger.error(f"[{self.name}] 최대 재연결 시도 횟수 초과")


class PollingNewsSource(NewsSource):
    """폴링 기반 소스 베이스 클래스

    재사용 가능한 폴링 로직 제공:
    - 폴링 루프
    - 중복 체크 (seen_ids)
    - 에러 핸들링
    """

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._running = False
        self._seen_ids: set[str] = set()

    async def connect(self) -> None:
        """연결 시작"""
        self._running = True
        self._seen_ids.clear()
        logger.info(f"[{self.name}] 폴링 시작 (간격: {self.interval}초)")

    async def disconnect(self) -> None:
        """연결 종료"""
        self._running = False
        logger.info(f"[{self.name}] 폴링 종료")

    @abstractmethod
    async def fetch(self) -> list[NewsItem]:
        """한 번 가져오기 (구현체에서 정의)

        Returns:
            NewsItem 리스트
        """
        pass

    async def stream(self) -> AsyncIterator[NewsItem]:
        """폴링 루프 (중복 제거 포함)"""
        while self._running:
            try:
                items = await self.fetch()
                logger.debug(f"[{self.name}] {len(items)}개 아이템 가져옴")

                for item in items:
                    if item.id not in self._seen_ids:
                        self._seen_ids.add(item.id)
                        yield item

            except Exception as e:
                logger.error(f"[{self.name}] Fetch 에러: {e}")

            await asyncio.sleep(self.interval)
