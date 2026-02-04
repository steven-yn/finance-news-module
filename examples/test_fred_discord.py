"""FRED 경제 지표 → Discord 통합 테스트

FRED 경제 지표 변화를 감지하여 Discord로 알림을 발송하는 전체 흐름을 테스트합니다.

필요한 환경변수:
- FRED_API_KEY: FRED API 키 (https://fred.stlouisfed.org/docs/api/api_key.html)
- DISCORD_WEBHOOK_URL: Discord Webhook URL

사용법:
    python examples/test_fred_discord.py
"""

import asyncio
import os
from datetime import datetime

from qfin.core.types import Alert
from qfin.notifiers.discord import DiscordNotifier

from finance_news.sources.fred import FREDSource


def news_item_to_alert(item) -> Alert:
    """NewsItem을 qfin Alert로 변환"""
    # 경제 지표는 symbol이 없으므로 "MARKET" 사용
    return Alert(
        symbol="MARKET",
        alert_type=f"ECON_{item.raw.get('series_id', 'INDICATOR')}",
        message=f"**{item.headline}**\n\n{item.summary}",
        current_value=item.raw.get("value", 0.0),
        change_percent=item.raw.get("change_percent", 0.0),
        timestamp=item.published_at,
        metadata={
            "source": item.source,
            "url": item.url,
            "category": item.category.value,
            "series_id": item.raw.get("series_id"),
            "change": item.raw.get("change"),
        },
    )


async def main():
    """메인 실행"""
    # 환경변수 확인
    api_key = os.getenv("FRED_API_KEY")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not api_key:
        print("❌ FRED_API_KEY 환경변수가 설정되지 않았습니다.")
        print("https://fred.stlouisfed.org/docs/api/api_key.html 에서 발급하세요.")
        return

    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("예: export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        return

    print("=" * 60)
    print("FRED 경제 지표 → Discord 통합 테스트")
    print("=" * 60)
    print()

    # 주요 경제 지표
    series_ids = [
        "DFF",  # 연방기금금리
        "CPIAUCSL",  # 소비자물가지수
        "UNRATE",  # 실업률
        "VIXCLS",  # VIX 지수
    ]

    # FRED 소스 생성
    fred_source = FREDSource(
        api_key=api_key,
        series_ids=series_ids,
        interval=60.0,  # 60초 폴링
        threshold_percent=0.01,  # 0.01% 이상 변화 시 알림
    )

    # Discord 알림기 생성
    notifier = DiscordNotifier(webhook_url=webhook_url)

    print("✅ FRED 소스 생성 완료")
    print(f"   - 모니터링 지표: {len(series_ids)}개")
    for series_id in series_ids:
        info = fred_source.KEY_INDICATORS.get(series_id, {})
        print(f"     • {series_id}: {info.get('name', series_id)}")
    print(f"   - 변화 임계값: {fred_source.threshold_percent}%")
    print()

    print("✅ Discord 알림기 생성 완료")
    print()

    # 연결
    await fred_source.connect()
    await notifier.start()

    print("🚀 통합 테스트 시작...")
    print("📊 FRED 경제 지표 → Discord 알림 전송")
    print()

    # 최대 5개 지표만 처리 (또는 120초 타임아웃)
    count = 0
    max_items = 5
    timeout = 120

    try:
        async for item in asyncio.wait_for(collect_items(fred_source, max_items), timeout=timeout):
            count += 1

            print(f"📊 [{count}/{max_items}] {item.headline}")
            print(f"   Published: {item.published_at}")
            print(f"   Change: {item.raw.get('change_percent', 0):+.2f}%")

            # Alert로 변환
            alert = news_item_to_alert(item)

            # Discord 발송
            try:
                await notifier.send(alert)
                print("   ✅ Discord 알림 발송 성공")
            except Exception as e:
                print(f"   ❌ Discord 알림 발송 실패: {e}")

            print()

            # 다음 지표 전 짧은 대기 (Discord Rate Limit 고려)
            await asyncio.sleep(1)

    except asyncio.TimeoutError:
        print(f"⏱️  {timeout}초 타임아웃. {count}개 지표 처리 완료.")

    finally:
        # 정리
        await fred_source.disconnect()
        await notifier.stop()

    print()
    print("=" * 60)
    print(f"✅ 통합 테스트 완료: {count}개 지표 → Discord 발송")
    print("=" * 60)


async def collect_items(source, max_items):
    """일정 개수만 수집"""
    count = 0
    async for item in source.stream():
        yield item
        count += 1
        if count >= max_items:
            break


if __name__ == "__main__":
    asyncio.run(main())
