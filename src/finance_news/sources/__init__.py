"""뉴스 소스 구현체"""

from .finnhub import FinnhubSource
from .sec import SECSource

# Phase 7, 9에서 구현될 소스들
# from .rss import RSSSource
# from .fred import FREDSource

__all__ = ["FinnhubSource", "SECSource"]
