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

    서브클래스에서 오버라이드 가능한 hook 메서드:
    - _on_connected(): 연결 직후 호출 (구독 등)
    - _parse_message(): 메시지 파싱
    - _process_message(): 메시지 처리 후 NewsItem 리스트 반환
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
        logger.info(f"[{self.name}] WebSocket 연결 시작")

    async def disconnect(self) -> None:
        """연결 종료"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info(f"[{self.name}] WebSocket 연결 종료")

    async def _on_connected(self, ws: websockets.WebSocketClientProtocol) -> None:
        """연결 직후 호출되는 hook (서브클래스에서 오버라이드)

        구독 메시지 전송 등에 활용
        """
        pass

    @abstractmethod
    async def _parse_message(self, data: dict) -> NewsItem | None:
        """단일 메시지 파싱 (구현체에서 정의)

        Args:
            data: WebSocket에서 받은 JSON 데이터

        Returns:
            NewsItem 또는 None (파싱 실패 시)
        """
        pass

    async def _process_message(self, data: dict) -> list[NewsItem]:
        """메시지 처리 후 NewsItem 리스트 반환

        배열 형태의 메시지를 처리해야 하는 경우 오버라이드.
        기본 구현은 _parse_message()를 호출하여 단일 아이템 반환.
        """
        item = await self._parse_message(data)
        return [item] if item else []

    async def stream(self) -> AsyncIterator[NewsItem]:
        """재연결 로직 포함 스트림"""
        retries = 0

        while self._running and retries < self.MAX_RETRIES:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    retries = 0
                    logger.info(f"[{self.name}] WebSocket 연결 성공")

                    # 연결 후 hook 호출 (구독 등)
                    await self._on_connected(ws)

                    async for message in ws:
                        if not self._running:
                            break

                        try:
                            data = json.loads(message)
                            items = await self._process_message(data)
                            for item in items:
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
    - 중복 체크 (seen_ids, LRU 방식 메모리 관리)
    - 에러 핸들링
    - 수동 새로고침 트리거
    """

    MAX_SEEN_IDS = 10000  # 최대 캐시 크기

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._running = False
        self._seen_ids: dict[str, None] = {}  # OrderedDict처럼 사용 (삽입 순서 유지)
        self._refresh_event = asyncio.Event()  # 수동 새로고침 트리거

    async def connect(self) -> None:
        """연결 시작"""
        self._running = True
        self._seen_ids.clear()
        logger.info(f"[{self.name}] 폴링 시작 (간격: {self.interval}초)")

    async def disconnect(self) -> None:
        """연결 종료"""
        self._running = False
        self._refresh_event.set()  # 대기 중인 sleep 깨우기
        logger.info(f"[{self.name}] 폴링 종료")

    def trigger_refresh(self) -> None:
        """수동 새로고침 트리거 (다음 폴링 즉시 실행)"""
        self._refresh_event.set()
        logger.info(f"[{self.name}] 수동 새로고침 트리거됨")

    def _add_seen_id(self, item_id: str) -> None:
        """seen_ids에 ID 추가 (LRU 방식으로 최대 크기 유지)"""
        self._seen_ids[item_id] = None

        # 최대 크기 초과 시 오래된 항목 제거
        while len(self._seen_ids) > self.MAX_SEEN_IDS:
            oldest_key = next(iter(self._seen_ids))
            del self._seen_ids[oldest_key]

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
                new_count = 0

                for item in items:
                    if item.id not in self._seen_ids:
                        self._add_seen_id(item.id)
                        new_count += 1
                        yield item

                logger.info(f"[{self.name}] {len(items)}개 중 {new_count}개 새 뉴스 발견")

            except Exception as e:
                logger.error(f"[{self.name}] Fetch 에러: {e}")

            # 수동 새로고침 또는 interval 대기
            self._refresh_event.clear()
            try:
                await asyncio.wait_for(
                    self._refresh_event.wait(),
                    timeout=self.interval,
                )
                logger.debug(f"[{self.name}] 수동 새로고침으로 폴링 재개")
            except asyncio.TimeoutError:
                pass  # 정상적인 interval 경과
