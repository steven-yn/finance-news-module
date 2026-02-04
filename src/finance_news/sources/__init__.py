"""뉴스 소스 구현체"""

from .finnhub import FinnhubSource
from .rss import RSSSource

# Phase 8-9에서 구현될 소스들
# from .sec import SECSource
# from .fred import FREDSource

__all__ = ["FinnhubSource", "RSSSource"]
