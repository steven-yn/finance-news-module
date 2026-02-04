"""핵심 추상화 계층"""

from .filter import CompositeFilter, NewsFilter, PassAllFilter
from .source import NewsSource, PollingNewsSource, WebSocketNewsSource
from .types import NewsAlert, NewsCategory, NewsItem

__all__ = [
    "NewsSource",
    "WebSocketNewsSource",
    "PollingNewsSource",
    "NewsFilter",
    "CompositeFilter",
    "PassAllFilter",
    "NewsItem",
    "NewsAlert",
    "NewsCategory",
]
