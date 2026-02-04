"""Finnhub WebSocket 뉴스 소스"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator, Optional

import websockets

from ..core.source import WebSocketNewsSource
from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class FinnhubSource(WebSocketNewsSource):
    """Finnhub WebSocket 뉴스 소스

    실시간 뉴스를 WebSocket을 통해 수신합니다.
    - 암호화폐 뉴스 (CRYPTO:BTC, CRYPTO:ETH 등)
    - 주식 뉴스 (AAPL, TSLA 등)
    """

    def __init__(self, api_key: str, symbols: list[str]):
        """
        Args:
            api_key: Finnhub API 키
            symbols: 구독할 심볼 리스트 (예: ["CRYPTO:BTC", "AAPL"])
        """
        url = f"wss://ws.finnhub.io?token={api_key}"
        super().__init__(url)
        self.api_key = api_key
        self.symbols = symbols

    @property
    def name(self) -> str:
        return "finnhub"

    async def connect(self) -> None:
        """연결 시작"""
        await super().connect()
        logger.info(f"[{self.name}] Will subscribe to {len(self.symbols)} symbols")

    async def _parse_message(self, data: dict) -> Optional[NewsItem]:
        """WebSocket 메시지 파싱

        Args:
            data: WebSocket에서 받은 JSON 데이터

        Returns:
            NewsItem 또는 None (뉴스 배열의 경우 첫 번째만 반환)

        Note:
            뉴스 메시지는 data 배열로 여러 개가 올 수 있습니다.
            stream()에서 배열을 순회하여 모두 yield합니다.
        """
        msg_type = data.get("type")

        # Ping 메시지는 무시
        if msg_type == "ping":
            logger.debug(f"[{self.name}] Received ping")
            return None

        # 뉴스 메시지 처리 - 베이스 클래스용으로 첫 번째만 반환
        # 실제로는 stream() 오버라이드에서 모든 아이템 처리
        if msg_type == "news":
            news_data = data.get("data", [])
            if news_data:
                return self._parse_news_item(news_data[0])

        # 알 수 없는 메시지 타입
        if msg_type and msg_type not in ["ping", "news"]:
            logger.warning(f"[{self.name}] Unknown message type: {msg_type}")

        return None

    def _parse_news_item(self, item: dict) -> Optional[NewsItem]:
        """뉴스 아이템 파싱

        Args:
            item: 뉴스 데이터 딕셔너리

        Returns:
            NewsItem 또는 None
        """
        try:
            # 필수 필드 확인
            news_id = item.get("id")
            headline = item.get("headline")

            if not news_id or not headline:
                logger.warning(f"[{self.name}] Missing required fields in news item")
                return None

            # 타임스탬프 파싱 (Unix timestamp in seconds)
            timestamp = item.get("datetime", 0)
            published_at = datetime.fromtimestamp(timestamp) if timestamp > 0 else datetime.utcnow()

            # 카테고리 결정
            category_str = item.get("category", "").lower()
            if "crypto" in category_str:
                category = NewsCategory.CRYPTO
            else:
                category = NewsCategory.BREAKING

            # 관련 심볼 파싱
            related = item.get("related", "")
            symbols = [related] if related else []

            return NewsItem(
                id=str(news_id),
                headline=headline,
                summary=item.get("summary"),
                url=item.get("url"),
                source=self.name,
                category=category,
                published_at=published_at,
                symbols=symbols,
                raw=item,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error parsing news item: {e}")
            return None

    async def stream(self) -> AsyncIterator[NewsItem]:
        """뉴스 스트림 (뉴스 배열 모두 처리)

        WebSocketNewsSource의 stream()을 오버라이드하여
        news 메시지의 data 배열을 모두 yield합니다.
        """
        retries = 0

        while self._running and retries < self.MAX_RETRIES:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    retries = 0

                    # 연결 시 구독
                    for symbol in self.symbols:
                        subscribe_msg = json.dumps({"type": "subscribe-news", "symbol": symbol})
                        await ws.send(subscribe_msg)
                        logger.info(f"[{self.name}] Subscribed to {symbol}")

                    logger.info(f"[{self.name}] WebSocket 연결 성공")

                    async for message in ws:
                        if not self._running:
                            break

                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")

                            # Ping 처리
                            if msg_type == "ping":
                                logger.debug(f"[{self.name}] Received ping")
                                continue

                            # 뉴스 처리 - 배열의 모든 아이템 yield
                            if msg_type == "news":
                                news_data = data.get("data", [])
                                for news_dict in news_data:
                                    item = self._parse_news_item(news_dict)
                                    if item:
                                        yield item

                        except json.JSONDecodeError as e:
                            logger.error(f"[{self.name}] JSON 파싱 실패: {e}")
                        except Exception as e:
                            logger.error(f"[{self.name}] 메시지 처리 실패: {e}")

            except websockets.exceptions.ConnectionClosed:
                retries += 1
                delay = min(self.BASE_DELAY * (2**retries), 60)
                logger.warning(
                    f"[{self.name}] 연결 끊김. {delay}초 후 재연결 시도 ({retries}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                retries += 1
                delay = min(self.BASE_DELAY * (2**retries), 60)
                logger.error(
                    f"[{self.name}] 연결 에러: {e}. {delay}초 후 재시도 ({retries}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)

        if retries >= self.MAX_RETRIES:
            logger.error(f"[{self.name}] 최대 재연결 시도 횟수 초과")
