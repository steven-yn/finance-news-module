"""SEC EDGAR 공시 소스

SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)에서
기업 공시 정보를 폴링 방식으로 수집합니다.

주요 기능:
- Form 8-K (중요 사건 즉시 공시)
- Form 10-K (연간 보고서)
- Form 10-Q (분기 보고서)
- Form 4 (내부자 거래)
- 회사별 최근 공시 모니터링
"""

import asyncio
import hashlib
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from ..core.source import PollingNewsSource
from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class SECSource(PollingNewsSource):
    """SEC EDGAR 공시 소스

    PollingNewsSource를 상속받아 주기적으로 SEC API를 폴링합니다.
    """

    BASE_URL = "https://data.sec.gov"
    MAX_REQUESTS_PER_SECOND = 10  # SEC rate limit
    RATE_LIMIT_WINDOW = 1.0  # 1초 윈도우

    def __init__(
        self,
        user_agent: str,
        ciks: list[str],
        form_types: Optional[list[str]] = None,
        interval: float = 60.0,
    ):
        """
        Args:
            user_agent: User-Agent 헤더 (이메일 포함 필수)
            ciks: 모니터링할 회사 CIK 리스트
            form_types: 필터링할 공시 유형 (예: ["8-K", "10-Q"])
            interval: 폴링 간격 (초)
        """
        super().__init__(interval)
        self.user_agent = user_agent
        self.ciks = ciks
        self.form_types = form_types or ["8-K", "10-K", "10-Q", "4"]
        self.headers = {"User-Agent": user_agent}
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_times: deque[float] = deque(maxlen=self.MAX_REQUESTS_PER_SECOND)
        self._cik_cache: dict[str, str] = {}  # CIK -> 회사명 캐시

    @property
    def name(self) -> str:
        return "sec_edgar"

    async def connect(self) -> None:
        """연결 시작 (HTTP 세션 생성)"""
        self._session = aiohttp.ClientSession(headers=self.headers)
        await super().connect()
        logger.info(
            f"[{self.name}] SEC EDGAR 모니터링 시작: {len(self.ciks)}개 회사, "
            f"공시 유형: {self.form_types}"
        )

    async def disconnect(self) -> None:
        """연결 종료 (HTTP 세션 해제)"""
        if self._session:
            await self._session.close()
            self._session = None
        await super().disconnect()

    async def _rate_limit(self) -> None:
        """Rate limit 준수 (슬라이딩 윈도우 방식, 초당 최대 10 요청)"""
        loop = asyncio.get_event_loop()
        now = loop.time()

        # 윈도우 내 요청 수가 최대치에 도달한 경우 대기
        if len(self._request_times) >= self.MAX_REQUESTS_PER_SECOND:
            oldest = self._request_times[0]
            time_since_oldest = now - oldest

            if time_since_oldest < self.RATE_LIMIT_WINDOW:
                wait_time = self.RATE_LIMIT_WINDOW - time_since_oldest
                logger.debug(f"[{self.name}] Rate limit 대기: {wait_time:.3f}초")
                await asyncio.sleep(wait_time)

        self._request_times.append(loop.time())

    async def _get_company_name(self, cik: str) -> str:
        """CIK로 회사명 가져오기 (캐시 사용)"""
        if cik in self._cik_cache:
            return self._cik_cache[cik]

        await self._rate_limit()
        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"

        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    company_name = data.get("name", f"CIK-{cik}")
                    self._cik_cache[cik] = company_name
                    return company_name
                else:
                    logger.warning(
                        f"[{self.name}] CIK {cik} 회사명 조회 실패: HTTP {response.status}"
                    )
                    return f"CIK-{cik}"

        except asyncio.TimeoutError:
            logger.warning(f"[{self.name}] CIK {cik} 회사명 조회 타임아웃")
            return f"CIK-{cik}"
        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] CIK {cik} 네트워크 에러: {e}")
            return f"CIK-{cik}"

    async def _get_recent_filings(self, cik: str, limit: int = 5) -> list[dict]:
        """특정 회사의 최근 공시 가져오기"""
        await self._rate_limit()

        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"

        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"[{self.name}] CIK {cik} 공시 조회 실패: {response.status}")
                    return []

                data = await response.json()
                recent = data.get("filings", {}).get("recent", {})

                if not recent:
                    return []

                # 컬럼형 데이터를 행 기반으로 변환
                filings = []
                accession_numbers = recent.get("accessionNumber", [])

                for i in range(len(accession_numbers)):
                    form = recent["form"][i]

                    # 공시 유형 필터링
                    if self.form_types and form not in self.form_types:
                        continue

                    filing = {
                        "cik": cik,
                        "accessionNumber": accession_numbers[i],
                        "filingDate": recent["filingDate"][i],
                        "reportDate": recent.get("reportDate", [None] * len(accession_numbers))[i],
                        "acceptanceDateTime": recent["acceptanceDateTime"][i],
                        "form": form,
                        "primaryDocument": recent["primaryDocument"][i],
                        "primaryDocDescription": recent.get(
                            "primaryDocDescription", [None] * len(accession_numbers)
                        )[i],
                        "companyName": data.get("name", f"CIK-{cik}"),
                        "ticker": data.get("tickers", [None])[0] if data.get("tickers") else None,
                    }

                    filings.append(filing)

                    if len(filings) >= limit:
                        break

                return filings

        except asyncio.TimeoutError:
            logger.warning(f"[{self.name}] CIK {cik} 공시 조회 타임아웃")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] CIK {cik} 네트워크 에러: {e}")
            return []
        except (KeyError, IndexError) as e:
            logger.error(f"[{self.name}] CIK {cik} 데이터 파싱 에러: {e}")
            return []

    def _filing_to_news_item(self, filing: dict) -> NewsItem:
        """SEC 공시를 NewsItem으로 변환"""
        # 고유 ID 생성 (accessionNumber 기반)
        item_id = hashlib.sha256(filing["accessionNumber"].encode()).hexdigest()[:16]

        # 공시 유형에 따라 카테고리 결정
        form_type = filing["form"]
        if form_type == "8-K":
            category = NewsCategory.BREAKING
        else:
            category = NewsCategory.SEC_FILING

        # 헤드라인 생성
        company_name = filing.get("companyName", f"CIK-{filing['cik']}")
        ticker = filing.get("ticker")
        ticker_str = f" ({ticker})" if ticker else ""
        desc = filing.get("primaryDocDescription") or form_type

        headline = f"{company_name}{ticker_str} - {desc}"

        # 요약 생성
        summary = f"Form {form_type} filed on {filing['filingDate']}"
        if filing.get("reportDate"):
            summary += f" (Report Date: {filing['reportDate']})"

        # 공시 문서 URL 생성
        accession = filing["accessionNumber"].replace("-", "")
        cik_stripped = str(int(filing["cik"]))
        primary_doc = filing["primaryDocument"]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession}/{primary_doc}"

        # 발행 시간 파싱
        try:
            published_at = datetime.fromisoformat(
                filing["acceptanceDateTime"].replace("Z", "+00:00")
            )
        except Exception:
            # fallback: filingDate 사용
            published_at = datetime.strptime(filing["filingDate"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )

        # 심볼 추출
        symbols = []
        if ticker:
            symbols.append(ticker)

        return NewsItem(
            id=item_id,
            headline=headline,
            summary=summary,
            url=url,
            source=self.name,
            category=category,
            published_at=published_at,
            symbols=symbols,
            raw=filing,
        )

    async def fetch(self) -> list[NewsItem]:
        """모든 회사의 최근 공시 가져오기"""
        if not self._session:
            raise RuntimeError("connect()를 먼저 호출해야 합니다")

        all_items = []

        for cik in self.ciks:
            try:
                filings = await self._get_recent_filings(cik, limit=5)

                for filing in filings:
                    item = self._filing_to_news_item(filing)
                    all_items.append(item)

            except Exception as e:
                logger.error(f"[{self.name}] CIK {cik} 처리 에러: {e}")

        logger.debug(f"[{self.name}] 총 {len(all_items)}개 공시 가져옴")
        return all_items
