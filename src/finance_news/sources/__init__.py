"""뉴스 소스 구현체"""

from .finnhub import FinnhubSource

# Phase 7-9에서 구현될 소스들
# from .rss import RSSSource
# from .sec import SECSource
# from .fred import FREDSource

__all__ = ["FinnhubSource"]
