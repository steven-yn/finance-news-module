"""SEC EDGAR 공시 소스

SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)에서
기업 공시 정보를 폴링 방식으로 수집합니다.

주요 기능:
- Form 8-K (중요 사건 즉시 공시)
- Form 10-K (연간 보고서)
- Form 10-Q (분기 보고서)
- Form 4 (내부자 거래)

참고: 개별 기업 공시 수집 기능은 제거되었습니다.
"""

import logging
from typing import Optional

import aiohttp

from ..core.source import PollingNewsSource
from ..core.types import NewsItem

logger = logging.getLogger(__name__)


class SECSource(PollingNewsSource):
    """SEC EDGAR 공시 소스

    PollingNewsSource를 상속받아 주기적으로 SEC API를 폴링합니다.
    개별 기업 공시 수집 기능은 제거되었습니다.
    """

    BASE_URL = "https://data.sec.gov"

    def __init__(
        self,
        user_agent: str,
        form_types: Optional[list[str]] = None,
        interval: float = 60.0,
    ):
        """
        Args:
            user_agent: User-Agent 헤더 (이메일 포함 필수)
            form_types: 필터링할 공시 유형 (예: ["8-K", "10-Q"])
            interval: 폴링 간격 (초)
        """
        super().__init__(interval)
        self.user_agent = user_agent
        self.form_types = form_types or ["8-K", "10-K", "10-Q", "4"]
        self.headers = {"User-Agent": user_agent}
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "sec_edgar"

    async def connect(self) -> None:
        """연결 시작 (HTTP 세션 생성)"""
        self._session = aiohttp.ClientSession(headers=self.headers)
        await super().connect()
        logger.info(f"[{self.name}] SEC EDGAR 모니터링 시작 (개별 기업 공시 수집 비활성화)")

    async def disconnect(self) -> None:
        """연결 종료 (HTTP 세션 해제)"""
        if self._session:
            await self._session.close()
            self._session = None
        await super().disconnect()

    async def fetch(self) -> list[NewsItem]:
        """공시 정보 가져오기 (현재 비활성화)"""
        if not self._session:
            raise RuntimeError("connect()를 먼저 호출해야 합니다")

        logger.debug(f"[{self.name}] 개별 기업 공시 수집이 비활성화되어 빈 리스트 반환")
        return []
