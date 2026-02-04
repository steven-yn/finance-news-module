"""RSS 피드 뉴스 소스"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional

import aiohttp
import feedparser

from ..core.source import PollingNewsSource
from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class MLStripper(HTMLParser):
    """HTML 태그 제거 유틸리티"""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return "".join(self.text)


def strip_html_tags(html: str) -> str:
    """HTML 태그 제거하여 텍스트만 추출

    Args:
        html: HTML이 포함된 문자열

    Returns:
        태그가 제거된 순수 텍스트
    """
    if not html:
        return ""

    s = MLStripper()
    try:
        s.feed(html)
        text = s.get_data()
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception as e:
        logger.warning(f"HTML 태그 제거 실패: {e}")
        return html


class RSSSource(PollingNewsSource):
    """RSS 피드 기반 뉴스 소스

    여러 RSS 피드를 폴링하여 뉴스를 수집합니다.
    PollingNewsSource를 상속받아 자동 폴링 및 중복 제거 기능 활용.
    """

    # 카테고리 매핑 (피드 URL 패턴 기반)
    CATEGORY_MAPPING = {
        "cnbc.com/id/100003114": NewsCategory.BREAKING,
        "cnbc.com/id/10000664": NewsCategory.BREAKING,
        "cnbc.com/id/20910258": NewsCategory.ECONOMIC,
        "bloomberg.com/markets": NewsCategory.ANALYSIS,
        "coindesk.com": NewsCategory.CRYPTO,
        "cointelegraph.com": NewsCategory.CRYPTO,
    }

    def __init__(
        self,
        feed_urls: list[str],
        interval: float = 120.0,
        timeout: int = 10,
    ):
        """RSS 소스 초기화

        Args:
            feed_urls: RSS 피드 URL 리스트
            interval: 폴링 간격 (초), 기본 120초 (2분)
            timeout: HTTP 요청 타임아웃 (초)
        """
        super().__init__(interval)
        self.feed_urls = feed_urls
        self.timeout = timeout
        feedparser.USER_AGENT = "FinanceNewsBot/1.0"

    @property
    def name(self) -> str:
        return "rss"

    async def fetch(self) -> list[NewsItem]:
        """모든 RSS 피드에서 뉴스 가져오기

        Returns:
            NewsItem 리스트
        """
        all_items = []

        for feed_url in self.feed_urls:
            try:
                items = await self._fetch_single_feed(feed_url)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"[{self.name}] 피드 처리 실패 ({feed_url}): {e}")

        all_items.sort(key=lambda x: x.published_at, reverse=True)
        return all_items

    async def _fetch_single_feed(self, feed_url: str) -> list[NewsItem]:
        """단일 RSS 피드 가져오기

        Args:
            feed_url: RSS 피드 URL

        Returns:
            NewsItem 리스트
        """
        try:
            feed_content = await self._fetch_feed_content(feed_url)

            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_content)

            if feed.bozo:
                logger.warning(f"[{self.name}] 피드 파싱 경고 ({feed_url}): {feed.bozo_exception}")

            items = []
            for entry in feed.entries:
                item = self._parse_entry(entry, feed_url)
                if item:
                    items.append(item)

            logger.debug(f"[{self.name}] {len(items)}개 아이템 파싱 완료 ({feed_url})")
            return items

        except asyncio.TimeoutError:
            logger.warning(f"[{self.name}] 피드 타임아웃 ({feed_url})")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] 피드 네트워크 에러 ({feed_url}): {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.name}] 피드 처리 실패 ({feed_url}): {e}")
            return []

    async def _fetch_feed_content(self, feed_url: str) -> str:
        """HTTP로 RSS 피드 콘텐츠 가져오기

        Args:
            feed_url: RSS 피드 URL

        Returns:
            RSS XML 문자열
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(feed_url, timeout=self.timeout) as response:
                response.raise_for_status()
                return await response.text()

    def _parse_entry(self, entry, feed_url: str) -> Optional[NewsItem]:
        """RSS 엔트리를 NewsItem으로 변환

        Args:
            entry: feedparser entry 객체
            feed_url: 소스 피드 URL

        Returns:
            NewsItem 또는 None (파싱 실패 시)
        """
        try:
            if not hasattr(entry, "title") or not hasattr(entry, "link"):
                return None

            item_id = hashlib.md5(entry.link.encode()).hexdigest()

            published_at = self._parse_published_date(entry)

            summary = self._extract_summary(entry)

            category = self._determine_category(feed_url)

            symbols = self._extract_symbols(entry)

            return NewsItem(
                id=item_id,
                headline=entry.title,
                summary=summary,
                url=entry.link,
                source=self._extract_source_name(feed_url),
                category=category,
                published_at=published_at,
                symbols=symbols,
                raw={
                    "feed_url": feed_url,
                    "author": getattr(entry, "author", None),
                    "tags": [tag.term for tag in getattr(entry, "tags", [])],
                },
            )

        except Exception as e:
            logger.error(f"[{self.name}] 엔트리 파싱 실패: {e}")
            return None

    def _parse_published_date(self, entry) -> datetime:
        """발행 날짜 파싱

        Args:
            entry: feedparser entry 객체

        Returns:
            발행 날짜 (UTC, 파싱 실패 시 현재 시간)
        """
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError) as e:
                logger.debug(f"날짜 파싱 실패: {e}")

        return datetime.now(timezone.utc)

    def _extract_summary(self, entry) -> Optional[str]:
        """요약 추출 및 HTML 태그 제거

        Args:
            entry: feedparser entry 객체

        Returns:
            요약 텍스트 (HTML 태그 제거됨)
        """
        summary_html = None
        if hasattr(entry, "summary"):
            summary_html = entry.summary
        elif hasattr(entry, "description"):
            summary_html = entry.description

        if summary_html:
            summary = strip_html_tags(summary_html)
            return summary[:500] if len(summary) > 500 else summary

        return None

    def _determine_category(self, feed_url: str) -> NewsCategory:
        """피드 URL 기반으로 카테고리 결정

        Args:
            feed_url: RSS 피드 URL

        Returns:
            NewsCategory
        """
        for pattern, category in self.CATEGORY_MAPPING.items():
            if pattern in feed_url:
                return category

        return NewsCategory.BREAKING

    def _extract_source_name(self, feed_url: str) -> str:
        """피드 URL에서 소스 이름 추출

        Args:
            feed_url: RSS 피드 URL

        Returns:
            소스 이름 (예: "cnbc", "bloomberg", "coindesk")
        """
        if "cnbc.com" in feed_url:
            return "cnbc"
        elif "bloomberg.com" in feed_url:
            return "bloomberg"
        elif "coindesk.com" in feed_url:
            return "coindesk"
        elif "cointelegraph.com" in feed_url:
            return "cointelegraph"
        else:
            return "rss"

    def _extract_symbols(self, entry) -> list[str]:
        """엔트리에서 심볼 추출 (태그 기반)

        Args:
            entry: feedparser entry 객체

        Returns:
            심볼 리스트
        """
        symbols = []

        if hasattr(entry, "tags"):
            for tag in entry.tags:
                tag_term = tag.term.upper()
                if any(keyword in tag_term for keyword in ["BTC", "BITCOIN"]):
                    symbols.append("BTC")
                elif any(keyword in tag_term for keyword in ["ETH", "ETHEREUM"]):
                    symbols.append("ETH")

        return list(set(symbols))
