"""핵심 데이터 타입 정의"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from qfin.core.types import Alert


class NewsCategory(Enum):
    """뉴스 카테고리"""

    BREAKING = "breaking"
    SEC_FILING = "sec_filing"
    ECONOMIC = "economic"
    ANALYSIS = "analysis"
    CRYPTO = "crypto"


@dataclass
class NewsItem:
    """뉴스 원본 데이터 (소스에서 수집된 raw 데이터)

    모든 뉴스 소스는 이 표준 형식으로 변환됨
    """

    id: str
    headline: str
    summary: Optional[str]
    url: Optional[str]
    source: str
    category: NewsCategory
    published_at: datetime
    symbols: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class NewsAlert(Alert):
    """뉴스 알림 (qfin Alert 확장)

    Discord 발송을 위해 Alert를 상속받아 뉴스 특화 필드 추가
    """

    headline: str = ""
    source: str = ""
    url: Optional[str] = None
    news_category: str = "NEWS"
