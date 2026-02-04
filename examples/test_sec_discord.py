"""SEC EDGAR → Discord 통합 테스트

SEC 공시를 수집하여 Discord로 알림을 발송하는 전체 흐름을 테스트합니다.

필요한 환경변수:
- SEC_USER_AGENT: SEC API User-Agent (예: "FinanceNews/1.0 admin@example.com")
- DISCORD_WEBHOOK_URL: Discord Webhook URL

사용법:
    python examples/test_sec_discord.py
"""

import asyncio
import os
from datetime import datetime

from qfin.core.types import Alert
from qfin.notifiers.discord import DiscordNotifier

from finance_news.sources.sec import SECSource


def news_item_to_alert(item) -> Alert:
    """NewsItem을 qfin Alert로 변환"""
    return Alert(
        symbol=item.symbols[0] if item.symbols else "MARKET",
        alert_type=f"SEC_{item.raw.get('form', 'FILING')}",
        message=f"**{item.headline}**\n\n{item.summary}",
        current_value=0.0,
        change_percent=0.0,
        timestamp=item.published_at,
        metadata={
            "source": item.source,
            "url": item.url,
            "category": item.category.value,
            "form_type": item.raw.get("form"),
            "filing_date": item.raw.get("filingDate"),
        },
    )


async def main():
    """메인 실행

    참고: 개별 기업 공시 수집 기능은 제거되었습니다.
    이 테스트는 빈 결과를 반환합니다.
    """
    # 환경변수 확인
    user_agent = os.getenv("SEC_USER_AGENT")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not user_agent:
        print("❌ SEC_USER_AGENT 환경변수가 설정되지 않았습니다.")
        print('예: export SEC_USER_AGENT="FinanceNews/1.0 admin@example.com"')
        return

    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("예: export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        return

    print("=" * 60)
    print("SEC EDGAR → Discord 통합 테스트 (비활성화)")
    print("=" * 60)
    print()

    # SEC 소스 생성
    sec_source = SECSource(
        user_agent=user_agent,
        form_types=["8-K"],  # 8-K (중요 사건) 공시만
        interval=60.0,
    )

    # Discord 알림기 생성
    notifier = DiscordNotifier(webhook_url=webhook_url)

    print("✅ SEC 소스 생성 완료")
    print(f"   - 공시 유형: 8-K")
    print(f"   - 개별 기업 공시 수집: 비활성화됨")
    print()

    print("✅ Discord 알림기 생성 완료")
    print()

    # 연결
    await sec_source.connect()
    await notifier.start()

    print("🚀 통합 테스트 시작...")
    print("📡 SEC 공시 → Discord 알림 전송")
    print()

    # 최대 5개 공시만 처리 (또는 120초 타임아웃)
    count = 0
    max_items = 5
    timeout = 120

    try:
        async for item in asyncio.wait_for(collect_items(sec_source, max_items), timeout=timeout):
            count += 1

            print(f"📄 [{count}/{max_items}] {item.headline}")
            print(f"   Published: {item.published_at}")
            print(f"   Form: {item.raw.get('form')}")

            # Alert로 변환
            alert = news_item_to_alert(item)

            # Discord 발송
            try:
                await notifier.send(alert)
                print("   ✅ Discord 알림 발송 성공")
            except Exception as e:
                print(f"   ❌ Discord 알림 발송 실패: {e}")

            print()

            # 다음 공시 전 짧은 대기 (Discord Rate Limit 고려)
            await asyncio.sleep(1)

    except asyncio.TimeoutError:
        print(f"⏱️  {timeout}초 타임아웃. {count}개 공시 처리 완료.")

    finally:
        # 정리
        await sec_source.disconnect()
        await notifier.stop()

    print()
    print("=" * 60)
    print(f"✅ 통합 테스트 완료: {count}개 공시 → Discord 발송")
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
