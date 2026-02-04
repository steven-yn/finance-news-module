"""Finnhub 소스 테스트"""

import asyncio
import os
from datetime import datetime

from finance_news.sources.finnhub import FinnhubSource


async def test_finnhub_connection():
    """Finnhub WebSocket 연결 테스트

    실제 API 키가 필요합니다. 환경변수 FINNHUB_API_KEY 설정 필요.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        print("⚠️  FINNHUB_API_KEY 환경변수가 설정되지 않았습니다.")
        print("테스트를 건너뜁니다.")
        return

    # 암호화폐 심볼
    symbols = ["CRYPTO:BTC", "CRYPTO:ETH"]

    source = FinnhubSource(api_key=api_key, symbols=symbols)

    print(f"✅ FinnhubSource 생성: {source.name}")
    print(f"📡 구독 심볼: {', '.join(symbols)}")
    print(f"🔗 WebSocket URL: wss://ws.finnhub.io?token=...")
    print()

    # 연결
    await source.connect()
    print("🔌 연결 시작...")
    print()

    # 10개 뉴스만 받고 종료
    count = 0
    max_items = 10
    timeout = 60  # 60초 타임아웃

    try:
        async for item in asyncio.wait_for(collect_items(source, max_items), timeout=timeout):
            count += 1
            print(f"📰 [{count}/{max_items}] {item.headline}")
            print(f"   Source: {item.source}")
            print(f"   Category: {item.category.value}")
            print(f"   Published: {item.published_at}")
            print(f"   Symbols: {', '.join(item.symbols)}")
            if item.url:
                print(f"   URL: {item.url}")
            print()

    except asyncio.TimeoutError:
        print(f"⏱️  {timeout}초 타임아웃. {count}개 뉴스 수신.")

    finally:
        # 연결 종료
        await source.disconnect()
        print("🔌 연결 종료")

    print(f"\n✅ 테스트 완료: {count}개 뉴스 수신")


async def collect_items(source, max_items):
    """일정 개수만 수집"""
    count = 0
    async for item in source.stream():
        yield item
        count += 1
        if count >= max_items:
            break


if __name__ == "__main__":
    print("=" * 60)
    print("Finnhub WebSocket 뉴스 소스 테스트")
    print("=" * 60)
    print()

    asyncio.run(test_finnhub_connection())
