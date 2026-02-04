"""FRED 경제 지표 소스 테스트"""

import asyncio
import os

from finance_news.sources.fred import FREDSource


async def collect_and_print_items(source, max_items):
    """아이템을 수집하고 출력"""
    count = 0
    async for item in source.stream():
        count += 1
        print(f"📊 [{count}/{max_items}] {item.headline}")
        print(f"   Source: {item.source}")
        print(f"   Category: {item.category.value}")
        print(f"   Published: {item.published_at}")
        print(f"   Summary: {item.summary}")
        if item.url:
            print(f"   URL: {item.url}")
        print()

        if count >= max_items:
            break

    return count


async def test_fred_connection():
    """FRED API 연결 테스트

    FRED_API_KEY 환경변수가 필요합니다.
    https://fred.stlouisfed.org/docs/api/api_key.html 에서 발급
    """
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        print("⚠️  FRED_API_KEY 환경변수가 설정되지 않았습니다.")
        print("https://fred.stlouisfed.org/docs/api/api_key.html 에서 발급하세요.")
        return

    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    # 주요 지표
    series_ids = [
        "DFF",  # 연방기금금리
        "CPIAUCSL",  # 소비자물가지수
        "UNRATE",  # 실업률
        "GDP",  # GDP
        "VIXCLS",  # VIX 지수
    ]

    source = FREDSource(
        api_key=api_key,
        series_ids=series_ids,
        interval=60.0,  # 60초 폴링 (테스트용)
        threshold_percent=0.01,  # 0.01% 이상 변화 시 알림
    )

    print(f"✅ FREDSource 생성: {source.name}")
    print(f"📊 모니터링 지표: {len(series_ids)}개")
    for series_id in series_ids:
        info = source.KEY_INDICATORS.get(series_id, {})
        print(f"   - {series_id}: {info.get('name', series_id)}")
    print(f"⏱️  폴링 간격: {source.interval}초")
    print(f"📈 변화 임계값: {source.threshold_percent}%")
    print()

    # 연결
    await source.connect()
    print("🔌 연결 시작...")
    print()

    # 최대 10개 또는 120초 타임아웃
    max_items = 10
    timeout = 120
    count = 0

    try:
        # 타임아웃 적용
        count = await asyncio.wait_for(collect_and_print_items(source, max_items), timeout=timeout)

    except asyncio.TimeoutError:
        print(f"⏱️  {timeout}초 타임아웃. {count}개 지표 수신.")

    finally:
        # 연결 종료
        await source.disconnect()
        print("🔌 연결 종료")

    print(f"\n✅ 테스트 완료: {count}개 지표 변화 감지")


async def test_fred_single_indicator():
    """단일 지표 테스트 (연방기금금리)"""
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        print("⚠️  FRED_API_KEY 환경변수가 설정되지 않았습니다.")
        return

    print("=" * 60)
    print("단일 지표 테스트: 연방기금금리 (DFF)")
    print("=" * 60)
    print()

    source = FREDSource(
        api_key=api_key,
        series_ids=["DFF"],  # 연방기금금리만
        interval=60.0,
        threshold_percent=0.0,  # 모든 변화 감지
    )

    await source.connect()
    print("🔌 연결 시작...")
    print()

    # 첫 번째 폴링 (초기 값)
    count = 0
    async for item in source.stream():
        count += 1
        print(f"📊 [{count}] {item.headline}")
        print(f"   {item.summary}")
        print()

        if count >= 1:  # 첫 값만
            break

    await source.disconnect()
    print(f"✅ {count}개 지표 수신 완료")


async def test_fred_critical_indicators():
    """중요 지표만 테스트 (critical importance)"""
    api_key = os.getenv("FRED_API_KEY")

    if not api_key:
        print("⚠️  FRED_API_KEY 환경변수가 설정되지 않았습니다.")
        return

    print("=" * 60)
    print("중요 지표 테스트 (Critical Indicators)")
    print("=" * 60)
    print()

    # critical importance만 필터링
    critical_series = [
        sid
        for sid, info in FREDSource.KEY_INDICATORS.items()
        if info.get("importance") == "critical"
    ]

    print(f"📊 중요 지표: {len(critical_series)}개")
    for sid in critical_series:
        info = FREDSource.KEY_INDICATORS[sid]
        print(f"   - {sid}: {info['name']}")
    print()

    source = FREDSource(
        api_key=api_key,
        series_ids=critical_series,
        interval=60.0,
        threshold_percent=0.0,  # 모든 변화 감지 (테스트용)
    )

    await source.connect()
    print("🔌 연결 시작...")
    print()

    count = 0
    async for item in source.stream():
        count += 1
        print(f"📊 [{count}] {item.headline}")
        print(f"   {item.summary}")
        print()

        if count >= len(critical_series):
            break

    await source.disconnect()
    print(f"✅ {count}개 지표 수신 완료")


if __name__ == "__main__":
    print("=" * 60)
    print("FRED 경제 지표 소스 테스트")
    print("=" * 60)
    print()

    # 기본 테스트
    asyncio.run(test_fred_connection())

    print("\n" + "=" * 60)
    print()

    # 단일 지표 테스트
    asyncio.run(test_fred_single_indicator())

    print("\n" + "=" * 60)
    print()

    # 중요 지표 테스트
    asyncio.run(test_fred_critical_indicators())
