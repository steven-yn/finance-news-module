"""통합 테스트

모든 소스 → 필터링 → Discord 알림 전체 흐름을 테스트합니다.

사용법:
    python tests/test_integration.py

필요한 환경변수:
    FINNHUB_API_KEY, FRED_API_KEY, DISCORD_WEBHOOK_URL (선택적)
"""

import asyncio
import logging
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance_news.core.filter import CompositeFilter
from finance_news.core.types import NewsCategory, NewsItem
from finance_news.filters import DeduplicationFilter, KeywordFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_test_news_item(
    headline: str,
    summary: str = "",
    source: str = "test",
    category: NewsCategory = NewsCategory.BREAKING,
    symbols: list[str] = None,
) -> NewsItem:
    """테스트용 NewsItem 생성"""
    import hashlib
    from datetime import datetime

    item_id = hashlib.sha256(headline.encode()).hexdigest()[:16]

    return NewsItem(
        id=item_id,
        headline=headline,
        summary=summary,
        url=f"https://example.com/{item_id}",
        source=source,
        category=category,
        published_at=datetime.now(),
        symbols=symbols or [],
        raw={},
    )


def test_keyword_filter():
    """키워드 필터 테스트"""
    print("\n" + "=" * 60)
    print("키워드 필터 테스트")
    print("=" * 60)

    # 암호화폐 프리셋으로 필터 생성
    filter = KeywordFilter(
        use_crypto_preset=True,
        use_market_preset=False,
    )

    test_cases = [
        # (헤드라인, 예상 결과)
        ("Bitcoin surges to new all-time high", True),
        ("Ethereum 2.0 upgrade complete", True),
        ("Apple announces new iPhone", False),
        ("Federal Reserve raises interest rates", False),
        ("Crypto market crashes amid regulatory concerns", True),
        ("BTC/USD trading volume hits record", True),
        ("Weather forecast for tomorrow", False),
    ]

    passed = 0
    failed = 0

    for headline, expected in test_cases:
        item = create_test_news_item(headline)
        result = filter.should_pass(item)

        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{headline[:40]}...' → {result} (예상: {expected})")

    print(f"\n결과: {passed} 통과, {failed} 실패")
    return failed == 0


def test_deduplication_filter():
    """중복 제거 필터 테스트"""
    print("\n" + "=" * 60)
    print("중복 제거 필터 테스트")
    print("=" * 60)

    filter = DeduplicationFilter(
        max_cache_size=100,
        ttl_seconds=3600.0,
    )

    # 첫 번째 뉴스 - 통과해야 함
    item1 = create_test_news_item("Bitcoin hits $100,000")
    result1 = filter.should_pass(item1)
    print(f"첫 번째 뉴스: {result1} (예상: True)")
    assert result1 is True, "첫 번째 뉴스는 통과해야 함"

    # 동일한 뉴스 - 차단해야 함
    item2 = create_test_news_item("Bitcoin hits $100,000")
    result2 = filter.should_pass(item2)
    print(f"중복 뉴스: {result2} (예상: False)")
    assert result2 is False, "중복 뉴스는 차단해야 함"

    # 다른 뉴스 - 통과해야 함
    item3 = create_test_news_item("Ethereum reaches new milestone")
    result3 = filter.should_pass(item3)
    print(f"새로운 뉴스: {result3} (예상: True)")
    assert result3 is True, "새로운 뉴스는 통과해야 함"

    print(f"\n캐시 크기: {filter.cache_size}")
    print("✅ 중복 제거 필터 테스트 통과")
    return True


def test_composite_filter():
    """복합 필터 테스트"""
    print("\n" + "=" * 60)
    print("복합 필터 테스트")
    print("=" * 60)

    # 키워드 필터 + 중복 제거 필터
    keyword_filter = KeywordFilter(
        include_keywords=["bitcoin", "crypto"],
        use_crypto_preset=False,
    )
    dedup_filter = DeduplicationFilter()

    composite = CompositeFilter([keyword_filter, dedup_filter])

    # 케이스 1: 키워드 매칭, 새로운 뉴스 → 통과
    item1 = create_test_news_item("Bitcoin price analysis")
    result1 = composite.should_pass(item1)
    print(f"키워드 매칭 + 새 뉴스: {result1} (예상: True)")
    assert result1 is True

    # 케이스 2: 키워드 매칭, 중복 뉴스 → 차단
    item2 = create_test_news_item("Bitcoin price analysis")
    result2 = composite.should_pass(item2)
    print(f"키워드 매칭 + 중복 뉴스: {result2} (예상: False)")
    assert result2 is False

    # 케이스 3: 키워드 미매칭 → 차단
    item3 = create_test_news_item("Apple stock rises")
    result3 = composite.should_pass(item3)
    print(f"키워드 미매칭: {result3} (예상: False)")
    assert result3 is False

    print("\n✅ 복합 필터 테스트 통과")
    return True


async def test_sec_source_integration():
    """SEC 소스 통합 테스트 (실제 API 호출)"""
    print("\n" + "=" * 60)
    print("SEC 소스 통합 테스트")
    print("=" * 60)

    from finance_news.sources import SECSource

    source = SECSource(
        user_agent="FinanceNews/1.0 test@example.com",
        ciks=["0000320193"],  # Apple만
        form_types=["8-K"],
        interval=60.0,
    )

    await source.connect()
    print("✅ SEC 소스 연결 성공")

    # 첫 번째 폴링
    count = 0
    async for item in source.stream():
        count += 1
        print(f"  📄 {item.headline}")
        if count >= 3:  # 3개만 확인
            break

    await source.disconnect()
    print(f"✅ SEC 소스 테스트 완료: {count}개 공시 수신")
    return count > 0


async def test_full_pipeline():
    """전체 파이프라인 테스트 (SEC → 필터 → 출력)"""
    print("\n" + "=" * 60)
    print("전체 파이프라인 테스트")
    print("=" * 60)

    from finance_news.sources import SECSource

    # 소스 생성
    source = SECSource(
        user_agent="FinanceNews/1.0 test@example.com",
        ciks=["0000320193", "0001318605"],  # Apple, Tesla
        form_types=["8-K", "10-K"],
        interval=60.0,
    )

    # 필터 생성
    keyword_filter = KeywordFilter(
        include_keywords=["apple", "tesla", "sec", "filing", "8-k", "10-k"],
        use_crypto_preset=False,
        use_market_preset=True,
    )
    dedup_filter = DeduplicationFilter()
    composite = CompositeFilter([dedup_filter, keyword_filter])

    # 실행
    await source.connect()

    passed = 0
    filtered = 0

    async for item in source.stream():
        if composite.should_pass(item):
            passed += 1
            print(f"  ✅ 통과: {item.headline[:50]}...")
        else:
            filtered += 1
            print(f"  ❌ 필터링: {item.headline[:50]}...")

        if passed + filtered >= 10:
            break

    await source.disconnect()

    print(f"\n결과: {passed}개 통과, {filtered}개 필터링됨")
    print("✅ 전체 파이프라인 테스트 완료")
    return True


def main():
    """테스트 실행"""
    print("=" * 60)
    print("Finance News 통합 테스트")
    print("=" * 60)

    # 단위 테스트
    test_keyword_filter()
    test_deduplication_filter()
    test_composite_filter()

    # 통합 테스트 (실제 API 호출)
    print("\n" + "=" * 60)
    print("실제 API 연동 테스트")
    print("=" * 60)

    asyncio.run(test_sec_source_integration())
    asyncio.run(test_full_pipeline())

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
