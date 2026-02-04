"""키워드 기반 뉴스 필터

특정 키워드를 포함하거나 제외하는 필터링을 제공합니다.

주요 기능:
- 포함 키워드 필터 (whitelist)
- 제외 키워드 필터 (blacklist)
- 대소문자 무시 옵션
- 암호화폐 관련 프리셋 키워드
"""

import logging
import re
from typing import Optional

from ..core.filter import NewsFilter
from ..core.types import NewsItem

logger = logging.getLogger(__name__)


class KeywordFilter(NewsFilter):
    """키워드 기반 뉴스 필터

    포함/제외 키워드 목록을 기반으로 뉴스를 필터링합니다.
    """

    # 암호화폐 관련 기본 키워드
    CRYPTO_KEYWORDS = [
        # 주요 코인
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "crypto",
        "cryptocurrency",
        "ripple",
        "xrp",
        "solana",
        "sol",
        "cardano",
        "ada",
        "dogecoin",
        "doge",
        "shiba",
        "bnb",
        "binance",
        # 관련 용어
        "blockchain",
        "defi",
        "nft",
        "web3",
        "stablecoin",
        "usdt",
        "usdc",
        "tether",
        "coinbase",
        "kraken",
        "mining",
        "halving",
        "altcoin",
        "token",
        # 규제 관련
        "sec crypto",
        "crypto regulation",
        "crypto etf",
    ]

    # 시장 관련 기본 키워드
    MARKET_KEYWORDS = [
        # 금리/경제
        "federal reserve",
        "fed rate",
        "interest rate",
        "inflation",
        "cpi",
        "ppi",
        "gdp",
        "unemployment",
        "jobs report",
        "fomc",
        "powell",
        "treasury",
        "bond yield",
        # 시장
        "stock market",
        "s&p 500",
        "nasdaq",
        "dow jones",
        "bull market",
        "bear market",
        "recession",
        "rally",
        # 기업
        "earnings",
        "revenue",
        "profit",
        "ipo",
        "merger",
        "acquisition",
        "sec filing",
        "8-k",
        "10-k",
        "10-q",
    ]

    def __init__(
        self,
        include_keywords: Optional[list[str]] = None,
        exclude_keywords: Optional[list[str]] = None,
        case_sensitive: bool = False,
        use_crypto_preset: bool = True,
        use_market_preset: bool = False,
        match_any: bool = True,
    ):
        """
        Args:
            include_keywords: 포함해야 할 키워드 목록 (None이면 모든 뉴스 통과)
            exclude_keywords: 제외해야 할 키워드 목록
            case_sensitive: 대소문자 구분 여부
            use_crypto_preset: 암호화폐 프리셋 키워드 사용
            use_market_preset: 시장 프리셋 키워드 사용
            match_any: True면 하나라도 매칭 시 통과, False면 모두 매칭 시 통과
        """
        self.case_sensitive = case_sensitive
        self.match_any = match_any

        # 포함 키워드 구성
        self.include_keywords: list[str] = []
        if include_keywords:
            self.include_keywords.extend(include_keywords)
        if use_crypto_preset:
            self.include_keywords.extend(self.CRYPTO_KEYWORDS)
        if use_market_preset:
            self.include_keywords.extend(self.MARKET_KEYWORDS)

        # 제외 키워드
        self.exclude_keywords = exclude_keywords or []

        # 대소문자 처리
        if not self.case_sensitive:
            self.include_keywords = [k.lower() for k in self.include_keywords]
            self.exclude_keywords = [k.lower() for k in self.exclude_keywords]

        # 중복 제거
        self.include_keywords = list(set(self.include_keywords))
        self.exclude_keywords = list(set(self.exclude_keywords))

        logger.info(
            f"KeywordFilter 초기화: "
            f"포함 {len(self.include_keywords)}개, "
            f"제외 {len(self.exclude_keywords)}개"
        )

    def _get_searchable_text(self, item: NewsItem) -> str:
        """뉴스 아이템에서 검색 가능한 텍스트 추출"""
        parts = [
            item.headline or "",
            item.summary or "",
            " ".join(item.symbols),
        ]
        text = " ".join(parts)

        if not self.case_sensitive:
            text = text.lower()

        return text

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """텍스트에 키워드가 포함되어 있는지 확인

        단어 경계를 고려하여 부분 매칭을 방지합니다.
        """
        # 단어 경계를 사용한 정규표현식
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE if not self.case_sensitive else 0))

    def should_pass(self, item: NewsItem) -> bool:
        """필터 통과 여부 판단

        1. 제외 키워드가 있으면 차단
        2. 포함 키워드가 비어있으면 통과
        3. 포함 키워드 중 하나라도 매칭되면 통과 (match_any=True)
        """
        text = self._get_searchable_text(item)

        # 1. 제외 키워드 체크
        for keyword in self.exclude_keywords:
            if self._contains_keyword(text, keyword):
                logger.debug(f"제외 키워드 매칭: '{keyword}' in '{item.headline}'")
                return False

        # 2. 포함 키워드가 없으면 통과
        if not self.include_keywords:
            return True

        # 3. 포함 키워드 체크
        if self.match_any:
            # 하나라도 매칭되면 통과
            for keyword in self.include_keywords:
                if self._contains_keyword(text, keyword):
                    logger.debug(f"포함 키워드 매칭: '{keyword}' in '{item.headline}'")
                    return True
            return False
        else:
            # 모두 매칭되어야 통과
            return all(self._contains_keyword(text, keyword) for keyword in self.include_keywords)


class CategoryFilter(NewsFilter):
    """카테고리 기반 필터

    특정 카테고리의 뉴스만 통과시킵니다.
    """

    def __init__(self, allowed_categories: list[str]):
        """
        Args:
            allowed_categories: 허용할 카테고리 목록 (예: ["breaking", "sec_filing"])
        """
        self.allowed_categories = [c.lower() for c in allowed_categories]
        logger.info(f"CategoryFilter 초기화: {self.allowed_categories}")

    def should_pass(self, item: NewsItem) -> bool:
        """카테고리가 허용 목록에 있으면 통과"""
        return item.category.value.lower() in self.allowed_categories


class SourceFilter(NewsFilter):
    """소스 기반 필터

    특정 소스의 뉴스만 통과시킵니다.
    """

    def __init__(self, allowed_sources: list[str]):
        """
        Args:
            allowed_sources: 허용할 소스 목록 (예: ["finnhub", "sec_edgar"])
        """
        self.allowed_sources = [s.lower() for s in allowed_sources]
        logger.info(f"SourceFilter 초기화: {self.allowed_sources}")

    def should_pass(self, item: NewsItem) -> bool:
        """소스가 허용 목록에 있으면 통과"""
        return item.source.lower() in self.allowed_sources
