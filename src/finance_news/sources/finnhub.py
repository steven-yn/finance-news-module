"""Finnhub WebSocket 뉴스 소스"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

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
        logger.info(f"[{self.name}] {len(self.symbols)}개 심볼 구독 예정")

    async def _on_connected(self, ws: websockets.WebSocketClientProtocol) -> None:
        """연결 후 심볼 구독"""
        for symbol in self.symbols:
            subscribe_msg = json.dumps({"type": "subscribe-news", "symbol": symbol})
            await ws.send(subscribe_msg)
            logger.debug(f"[{self.name}] 구독: {symbol}")
        logger.info(f"[{self.name}] {len(self.symbols)}개 심볼 구독 완료")

    async def _process_message(self, data: dict) -> list[NewsItem]:
        """메시지 처리 (배열 형태의 뉴스 처리)"""
        msg_type = data.get("type")

        # Ping 메시지는 무시
        if msg_type == "ping":
            logger.debug(f"[{self.name}] Received ping")
            return []

        # 뉴스 메시지 처리 - 배열의 모든 아이템 반환
        if msg_type == "news":
            news_data = data.get("data", [])
            items = []
            for news_dict in news_data:
                item = self._parse_news_item(news_dict)
                if item:
                    items.append(item)
            return items

        # 알 수 없는 메시지 타입
        if msg_type and msg_type not in ["ping", "news"]:
            logger.warning(f"[{self.name}] Unknown message type: {msg_type}")

        return []

    async def _parse_message(self, data: dict) -> Optional[NewsItem]:
        """단일 메시지 파싱 (베이스 클래스 인터페이스 충족용)

        Note: 실제 처리는 _process_message()에서 수행
        """
        msg_type = data.get("type")
        if msg_type == "news":
            news_data = data.get("data", [])
            if news_data:
                return self._parse_news_item(news_data[0])
        return None

    def _parse_news_item(self, item: dict) -> Optional[NewsItem]:
        """뉴스 아이템 파싱

        Args:
            item: 뉴스 데이터 딕셔너리

        Returns:
            NewsItem 또는 None
        """
        try:
            news_id = item.get("id")
            headline = item.get("headline")

            if not news_id or not headline:
                logger.warning(f"[{self.name}] Missing required fields in news item")
                return None

            # 타임스탬프 파싱 (Unix timestamp in seconds)
            timestamp = item.get("datetime", 0)
            if timestamp > 0:
                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                published_at = datetime.now(timezone.utc)

            # 카테고리 결정
            category_str = item.get("category", "").lower()
            category = NewsCategory.CRYPTO if "crypto" in category_str else NewsCategory.BREAKING

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
