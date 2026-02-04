"""FRED (Federal Reserve Economic Data) 경제 지표 소스

미국 연방준비제도 세인트루이스 은행의 경제 데이터를 수집합니다.

주요 기능:
- 주요 경제 지표 모니터링 (금리, 실업률, CPI, GDP 등)
- 데이터 변화 감지 (신규 값 발표 시)
- 중요한 변화 필터링 (임계값 기반)
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fredapi import Fred

from ..core.source import PollingNewsSource
from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class FREDSource(PollingNewsSource):
    """FRED 경제 지표 소스

    PollingNewsSource를 상속받아 주기적으로 경제 지표를 폴링합니다.
    """

    # 주요 경제 지표 정의
    KEY_INDICATORS = {
        "DFF": {
            "name": "Federal Funds Rate",
            "unit": "%",
            "importance": "critical",
            "description": "연방기금금리 (미국 기준금리)",
        },
        "CPIAUCSL": {
            "name": "Consumer Price Index",
            "unit": "Index",
            "importance": "critical",
            "description": "소비자물가지수 (인플레이션 지표)",
        },
        "UNRATE": {
            "name": "Unemployment Rate",
            "unit": "%",
            "importance": "critical",
            "description": "실업률 (노동시장 건강도)",
        },
        "GDP": {
            "name": "Gross Domestic Product",
            "unit": "Billions USD",
            "importance": "high",
            "description": "국내총생산 (경제 규모)",
        },
        "M2SL": {
            "name": "M2 Money Supply",
            "unit": "Billions USD",
            "importance": "medium",
            "description": "통화량 M2",
        },
        "VIXCLS": {
            "name": "VIX Volatility Index",
            "unit": "Index",
            "importance": "high",
            "description": "시장 변동성 지표 (공포 지수)",
        },
        "T10Y2Y": {
            "name": "10-Year Treasury Minus 2-Year",
            "unit": "%",
            "importance": "high",
            "description": "10년-2년 국채 금리 스프레드 (경기 침체 신호)",
        },
    }

    def __init__(
        self,
        api_key: str,
        series_ids: Optional[list[str]] = None,
        interval: float = 3600.0,  # 1시간 (경제 지표는 자주 업데이트되지 않음)
        threshold_percent: float = 0.1,  # 0.1% 이상 변화 시 알림
    ):
        """
        Args:
            api_key: FRED API 키
            series_ids: 모니터링할 시계열 ID 리스트 (None이면 KEY_INDICATORS 사용)
            interval: 폴링 간격 (초)
            threshold_percent: 변화율 임계값 (%)
        """
        super().__init__(interval)
        self.api_key = api_key
        self.series_ids = series_ids or list(self.KEY_INDICATORS.keys())
        self.threshold_percent = threshold_percent
        self._fred: Optional[Fred] = None
        self._last_values: dict[str, float] = {}  # 마지막 값 저장

    @property
    def name(self) -> str:
        return "fred"

    async def connect(self) -> None:
        """연결 시작 (FRED 클라이언트 생성)"""
        self._fred = Fred(api_key=self.api_key)
        await super().connect()
        logger.info(
            f"[{self.name}] FRED 경제 지표 모니터링 시작: "
            f"{len(self.series_ids)}개 지표, "
            f"임계값: {self.threshold_percent}%"
        )

    async def disconnect(self) -> None:
        """연결 종료"""
        self._fred = None
        await super().disconnect()

    async def _get_latest_value(self, series_id: str) -> Optional[dict]:
        """최신 값 가져오기 (비동기 래퍼)"""
        if not self._fred:
            raise RuntimeError("connect()를 먼저 호출해야 합니다")

        try:
            # 최근 3개월 데이터 (최신 값 + 이전 값)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=90)

            # fredapi는 동기 API이므로 실행자로 실행
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._fred.get_series(
                    series_id,
                    observation_start=start_date.strftime("%Y-%m-%d"),
                    observation_end=end_date.strftime("%Y-%m-%d"),
                ),
            )

            if len(data) < 1:
                return None

            latest_value = data.iloc[-1]
            latest_date = data.index[-1]

            # 이전 값 (변화 계산용)
            previous_value = data.iloc[-2] if len(data) >= 2 else latest_value
            change = latest_value - previous_value
            change_percent = (change / previous_value) * 100 if previous_value != 0 else 0

            return {
                "series_id": series_id,
                "date": latest_date,
                "value": latest_value,
                "previous_value": previous_value,
                "change": change,
                "change_percent": change_percent,
            }

        except Exception as e:
            logger.error(f"[{self.name}] {series_id} 조회 에러: {e}")
            return None

    def _should_alert(self, series_id: str, current_value: float) -> bool:
        """알림 여부 판단

        Args:
            series_id: 시계열 ID
            current_value: 현재 값

        Returns:
            True if 신규 값이거나 중요한 변화가 있음
        """
        # 첫 번째 수집
        if series_id not in self._last_values:
            self._last_values[series_id] = current_value
            return True  # 첫 수집은 항상 알림

        last_value = self._last_values[series_id]

        # 값이 동일하면 알림 안 함
        if current_value == last_value:
            return False

        # 변화율 계산
        if last_value != 0:
            change_percent = abs((current_value - last_value) / last_value) * 100
        else:
            change_percent = 100.0  # 0에서 변화하면 큰 변화로 간주

        # 임계값 초과 시 알림
        if change_percent >= self.threshold_percent:
            self._last_values[series_id] = current_value
            return True

        return False

    def _indicator_to_news_item(self, indicator_data: dict) -> NewsItem:
        """경제 지표 데이터를 NewsItem으로 변환"""
        series_id = indicator_data["series_id"]
        info = self.KEY_INDICATORS.get(series_id, {})

        # 고유 ID 생성 (시계열 ID + 날짜)
        date_str = indicator_data["date"].strftime("%Y-%m-%d")
        item_id = hashlib.sha256(f"{series_id}-{date_str}".encode()).hexdigest()[:16]

        # 헤드라인 생성
        name = info.get("name", series_id)
        value = indicator_data["value"]
        unit = info.get("unit", "")
        change = indicator_data["change"]
        change_pct = indicator_data["change_percent"]

        # 변화 방향 아이콘
        if change > 0:
            direction = "↗️"
            trend = "increased"
        elif change < 0:
            direction = "↘️"
            trend = "decreased"
        else:
            direction = "→"
            trend = "unchanged"

        headline = f"{direction} {name}: {value:.2f} {unit}"

        # 요약 생성
        summary = (
            f"{name} {trend} to {value:.2f} {unit} "
            f"({change:+.2f}, {change_pct:+.2f}%) on {date_str}. "
        )

        if info.get("description"):
            summary += f"\n{info['description']}"

        # 중요도에 따른 카테고리
        importance = info.get("importance", "medium")
        if importance == "critical":
            category = NewsCategory.BREAKING
        else:
            category = NewsCategory.ECONOMIC

        # FRED 시계열 URL
        url = f"https://fred.stlouisfed.org/series/{series_id}"

        return NewsItem(
            id=item_id,
            headline=headline,
            summary=summary,
            url=url,
            source=self.name,
            category=category,
            published_at=datetime.combine(
                indicator_data["date"], datetime.min.time(), tzinfo=timezone.utc
            ),
            symbols=[],  # 경제 지표는 특정 심볼이 없음
            raw=indicator_data,
        )

    async def fetch(self) -> list[NewsItem]:
        """모든 지표의 최신 값 가져오기"""
        if not self._fred:
            raise RuntimeError("connect()를 먼저 호출해야 합니다")

        items = []

        for series_id in self.series_ids:
            try:
                # 최신 값 가져오기
                indicator_data = await self._get_latest_value(series_id)

                if not indicator_data:
                    continue

                # 알림 여부 판단 (신규 값이거나 중요한 변화)
                if self._should_alert(series_id, indicator_data["value"]):
                    item = self._indicator_to_news_item(indicator_data)
                    items.append(item)
                    logger.debug(
                        f"[{self.name}] {series_id}: "
                        f"{indicator_data['value']:.2f} "
                        f"({indicator_data['change_percent']:+.2f}%)"
                    )

            except Exception as e:
                logger.error(f"[{self.name}] {series_id} 처리 에러: {e}")

        if items:
            logger.info(f"[{self.name}] {len(items)}개 지표 변화 감지")

        return items
