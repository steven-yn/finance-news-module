"""SEC EDGAR 소스 테스트"""

import asyncio
import os

from finance_news.sources.sec import SECSource


async def collect_and_print_items(source, max_items):
    """아이템을 수집하고 출력"""
    count = 0
    async for item in source.stream():
        count += 1
        print(f"📄 [{count}/{max_items}] {item.headline}")
        print(f"   Source: {item.source}")
        print(f"   Category: {item.category.value}")
        print(f"   Published: {item.published_at}")
        print(f"   Summary: {item.summary}")
        print(f"   Symbols: {', '.join(item.symbols) if item.symbols else 'N/A'}")
        if item.url:
            print(f"   URL: {item.url}")
        print()

        if count >= max_items:
            break

    return count


async def test_sec_connection():
    """SEC EDGAR API 연결 테스트

    User-Agent가 필요합니다. 환경변수 SEC_USER_AGENT 설정 필요.
    예: "FinanceNews/1.0 admin@example.com"

    참고: 개별 기업 공시 수집 기능은 제거되었습니다.
    """
    user_agent = os.getenv("SEC_USER_AGENT", "FinanceNews/1.0 test@example.com")

    print(f"🔑 User-Agent: {user_agent}")
    print()

    form_types = ["8-K", "10-K", "10-Q"]  # 주요 공시 유형만

    source = SECSource(
        user_agent=user_agent,
        form_types=form_types,
        interval=60.0,  # 60초 폴링
    )

    print(f"✅ SECSource 생성: {source.name}")
    print(f"📋 공시 유형: {', '.join(form_types)}")
    print(f"⏱️  폴링 간격: {source.interval}초")
    print(f"ℹ️  개별 기업 공시 수집: 비활성화됨")
    print()

    # 연결
    await source.connect()
    print("🔌 연결 시작...")
    print()

    # 10개 공시만 받고 종료 (또는 120초 타임아웃)
    max_items = 10
    timeout = 120
    count = 0

    try:
        # 타임아웃 적용
        count = await asyncio.wait_for(collect_and_print_items(source, max_items), timeout=timeout)

    except asyncio.TimeoutError:
        print(f"⏱️  {timeout}초 타임아웃. {count}개 공시 수신.")

    finally:
        # 연결 종료
        await source.disconnect()
        print("🔌 연결 종료")

    print(f"\n✅ 테스트 완료: {count}개 공시 수신")


async def test_sec_single_company():
    """개별 기업 공시 테스트 (비활성화됨)"""
    user_agent = os.getenv("SEC_USER_AGENT", "FinanceNews/1.0 test@example.com")

    print("=" * 60)
    print("개별 기업 공시 테스트 (비활성화)")
    print("=" * 60)
    print()

    source = SECSource(
        user_agent=user_agent,
        form_types=["8-K"],  # 8-K (중요 사건) 만
        interval=60.0,
    )

    await source.connect()
    print("🔌 연결 시작...")
    print()

    # 빈 리스트 반환 확인
    count = 0
    async for item in source.stream():
        count += 1
        print(f"📄 [{count}] {item.headline}")
        print(f"   {item.summary}")
        print()

        if count >= 5:
            break

    await source.disconnect()
    print(f"ℹ️  개별 기업 공시 수집 비활성화: {count}개 수신 (0개 예상)")


if __name__ == "__main__":
    print("=" * 60)
    print("SEC EDGAR 공시 소스 테스트")
    print("=" * 60)
    print()

    # 기본 테스트
    asyncio.run(test_sec_connection())

    print("\n" + "=" * 60)
    print()

    # 단일 회사 테스트
    asyncio.run(test_sec_single_company())
