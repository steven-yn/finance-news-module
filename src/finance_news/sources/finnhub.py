"""Finnhub REST API 뉴스 소스"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from ..core.source import PollingNewsSource
from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class FinnhubSource(PollingNewsSource):
    """Finnhub REST API 뉴스 소스

    REST API를 통해 주기적으로 뉴스를 폴링합니다.
    - 일반 뉴스 (category=general)
    - 암호화폐 뉴스 (category=crypto)
    - 외환 뉴스 (category=forex)
    - 병합 뉴스 (category=merger)

    참고: WebSocket 뉴스 구독은 유료 플랜 전용이므로 REST API 사용
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(
        self,
        api_key: str,
        categories: list[str] = None,
        interval: float = 300.0,
    ):
        """
        Args:
            api_key: Finnhub API 키
            categories: 뉴스 카테고리 리스트 (기본값: ["general", "crypto"])
            interval: 폴링 간격 (초), 기본 300초 (5분)
        """
        super().__init__(interval)
        self.api_key = api_key
        self.categories = categories or ["general", "crypto"]
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "finnhub"

    async def connect(self) -> None:
        """연결 시작 (HTTP 세션 생성)"""
        self._session = aiohttp.ClientSession()
        await super().connect()
        logger.info(f"[{self.name}] Finnhub REST API 뉴스 폴링 시작: {', '.join(self.categories)}")

    async def disconnect(self) -> None:
        """연결 종료 (HTTP 세션 해제)"""
        if self._session:
            await self._session.close()
            self._session = None
        await super().disconnect()

    async def fetch(self) -> list[NewsItem]:
        """모든 카테고리의 뉴스 가져오기"""
        if not self._session:
            raise RuntimeError("connect()를 먼저 호출해야 합니다")

        all_items = []

        for category in self.categories:
            try:
                items = await self._fetch_category_news(category)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"[{self.name}] 카테고리 {category} 뉴스 조회 에러: {e}")

        # 발행 시간 기준 내림차순 정렬
        all_items.sort(key=lambda x: x.published_at, reverse=True)

        logger.debug(f"[{self.name}] 총 {len(all_items)}개 뉴스 가져옴")
        return all_items

    async def _fetch_category_news(self, category: str) -> list[NewsItem]:
        """특정 카테고리의 뉴스 가져오기

        Args:
            category: 뉴스 카테고리 (general, crypto, forex, merger)

        Returns:
            NewsItem 리스트
        """
        url = f"{self.BASE_URL}/news"
        params = {
            "category": category,
            "token": self.api_key,
        }

        try:
            async with self._session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning(
                        f"[{self.name}] 뉴스 조회 실패 (category={category}): "
                        f"HTTP {response.status}"
                    )
                    return []

                data = await response.json()

                if not isinstance(data, list):
                    logger.warning(f"[{self.name}] 잘못된 응답 형식: {type(data)}")
                    return []

                items = []
                for news_dict in data:
                    item = self._parse_news_item(news_dict, category)
                    if item:
                        items.append(item)

                logger.debug(f"[{self.name}] 카테고리 {category}: {len(items)}개 뉴스 파싱 완료")
                return items

        except asyncio.TimeoutError:
            logger.warning(f"[{self.name}] 뉴스 조회 타임아웃 (category={category})")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] 네트워크 에러 (category={category}): {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.name}] 뉴스 조회 실패 (category={category}): {e}")
            return []

    def _parse_news_item(self, item: dict, category: str) -> Optional[NewsItem]:
        """뉴스 아이템 파싱

        Args:
            item: 뉴스 데이터 딕셔너리
            category: 뉴스 카테고리

        Returns:
            NewsItem 또는 None
        """
        try:
            news_id = item.get("id")
            headline = item.get("headline")

            if not news_id or not headline:
                logger.debug(f"[{self.name}] 필수 필드 누락 (id 또는 headline)")
                return None

            # 타임스탬프 파싱 (Unix timestamp in seconds)
            timestamp = item.get("datetime", 0)
            if timestamp > 0:
                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                published_at = datetime.now(timezone.utc)

            # 카테고리 결정
            news_category_str = item.get("category", "").lower()
            if "crypto" in category or "crypto" in news_category_str:
                news_category = NewsCategory.CRYPTO
            elif category == "merger" or "merger" in news_category_str:
                news_category = NewsCategory.BREAKING
            else:
                news_category = NewsCategory.BREAKING

            # 관련 심볼 파싱
            related = item.get("related", "")
            symbols = [s.strip() for s in related.split(",") if s.strip()] if related else []

            # 고유 ID 생성 (Finnhub ID + 카테고리 해시)
            unique_id = hashlib.md5(f"{news_id}_{category}".encode()).hexdigest()[:16]

            return NewsItem(
                id=unique_id,
                headline=headline,
                summary=item.get("summary"),
                url=item.get("url"),
                source=item.get("source", self.name),
                category=news_category,
                published_at=published_at,
                symbols=symbols,
                raw=item,
            )

        except Exception as e:
            logger.error(f"[{self.name}] 뉴스 아이템 파싱 에러: {e}")
            return None
