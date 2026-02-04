# RSS 피드 API 문서

## 개요

RSS (Really Simple Syndication)는 뉴스 및 블로그 업데이트를 배포하는 표준 XML 형식입니다. 무료이며 API 키가 필요하지 않습니다.

### 장점
- ✅ **완전 무료**: API 키 불필요
- ✅ **신뢰할 수 있는 출처**: 전통 미디어 (CNBC, Reuters 등)
- ✅ **표준화된 형식**: RSS 2.0, Atom 등 표준 지원
- ✅ **간단한 구현**: HTTP GET 요청만으로 충분

---

## RSS 피드 목록

### 1. CNBC (Consumer News and Business Channel)

#### Top News
```
URL: https://www.cnbc.com/id/100003114/device/rss/rss.html
카테고리: 주요 뉴스
업데이트: 실시간
```

#### Finance (검증됨 ✅)
```
URL: https://www.cnbc.com/id/10000664/device/rss/rss.html
카테고리: 월스트리트 투자/금융 뉴스
업데이트: 실시간
TTL: 60분
```

#### Economy (검증됨 ✅)
```
URL: https://www.cnbc.com/id/20910258/device/rss/rss.html
카테고리: 경제 뉴스 (고용, 무역, 인플레이션)
업데이트: 실시간
TTL: 60분
```

#### Crypto News (비활성 ❌)
```
URL: https://www.cnbc.com/id/33002080/device/rss/rss.html
상태: 404 에러 - 피드 중단됨
대안: CNBC Finance 피드에서 암호화폐 뉴스 포함
```

#### Technology
```
URL: https://www.cnbc.com/id/19854910/device/rss/rss.html
카테고리: 기술 뉴스
업데이트: 실시간
```

**참고**: 
- CNBC RSS 피드는 무료로 제공됩니다
- 공식 RSS 피드 목록: https://www.cnbc.com/rss-feeds/

### 2. Reuters (비권장 ⚠️)

**상태**: 공식 RSS 피드 비활성화

과거 URL (현재 작동하지 않음):
```
URL: https://www.reutersagency.com/feed/
상태: 공식 RSS 피드 중단
```

**대안**:
- 서드파티 RSS 생성 도구 (rss.app, Newsloth)
- Bloomberg 또는 다른 소스 사용 권장

### 3. Bloomberg (검증됨 ✅)

#### Markets News
```
URL: https://feeds.bloomberg.com/markets/news.rss
카테고리: 글로벌 시장 뉴스
업데이트: 실시간
기사 수: 약 30개
```

**특징**:
- 기업 실적, M&A, 주요 인물 인터뷰
- 지정학적 이슈 포함
- 고품질 분석 기사

**XML 네임스페이스**:
- Dublin Core (`dc`)
- Media RSS (`mrss`)
- Atom
- Content

#### Technology
```
URL: https://feeds.bloomberg.com/technology/news.rss
카테고리: 기술
업데이트: 실시간
```

### 4. CoinDesk (검증됨 ✅)

#### Latest News
```
URL: https://www.coindesk.com/arc/outboundfeeds/rss/
카테고리: Bitcoin, Ethereum, DeFi, Web3
업데이트: 1시간 단위
언어: en-US
```

**특징**:
- 암호화폐 전문 미디어
- BTC/ETH 가격 분석
- DeFi 프로토콜 뉴스
- 규제 동향

**XML 네임스페이스**:
- `dc:creator`: 작성자
- `media:content`: 썸네일 이미지
- `category`: 토픽 태그

### 5. Cointelegraph (검증됨 ✅)

#### Latest News
```
URL: https://cointelegraph.com/rss
카테고리: 블록체인, 핀테크, 암호화폐
업데이트: 1시간 단위
언어: English
```

**특징**:
- 블록체인/핀테크 전문
- 풍부한 메타데이터
- 기술적 분석
- 프로젝트 펀딩 뉴스

**XML 네임스페이스**:
- `dc:creator`: 작성자
- `media:content`: 이미지 URL 및 메타데이터
- `enclosure`: 첨부 파일
- `category`: 다중 태그 지원

**샘플 콘텐츠**:
- Bitcoin 가격 분석
- Vitalik Buterin 발언
- L2 솔루션 뉴스
- 투자 라운드 소식

---

## Python feedparser 라이브러리

### 설치

```bash
pip install feedparser
```

### 기본 사용법

```python
import feedparser

# URL에서 피드 파싱
feed = feedparser.parse('https://www.cnbc.com/id/100003114/device/rss/rss.html')

# 피드 메타데이터
print(f"Feed Title: {feed.feed.title}")
print(f"Feed Description: {feed.feed.description}")

# 엔트리(기사) 순회
for entry in feed.entries:
    print(f"Title: {entry.title}")
    print(f"Link: {entry.link}")
    print(f"Published: {entry.published}")
    print(f"Summary: {entry.summary}")
```

---

## RSS 피드 구조

### Feed Level (피드 전체)

```python
feed.feed.title          # 피드 제목
feed.feed.description    # 피드 설명
feed.feed.link           # 피드 링크
feed.feed.language       # 언어 (예: en-us)
feed.feed.updated        # 마지막 업데이트 시간
```

### Entry Level (개별 기사)

```python
entry.title              # 기사 제목
entry.link               # 기사 링크
entry.published          # 발행 시간 (문자열)
entry.published_parsed   # 발행 시간 (struct_time)
entry.summary            # 요약/설명
entry.id                 # 고유 ID
entry.author             # 작성자 (있는 경우)
entry.tags               # 태그/카테고리 (있는 경우)
```

### 날짜 처리

```python
import time
from datetime import datetime

# struct_time을 datetime으로 변환
if hasattr(entry, 'published_parsed') and entry.published_parsed:
    dt = datetime(*entry.published_parsed[:6])
    print(f"Published: {dt.isoformat()}")
```

---

## 전체 구현 예제

### RSS 피드 파서 클래스

```python
import feedparser
import hashlib
from datetime import datetime
from typing import List, Optional

class RSSFeedParser:
    """RSS 피드 파서
    
    여러 RSS 피드를 파싱하고 표준화된 형식으로 반환
    """
    
    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls
    
    def parse_feed(self, url: str) -> List[dict]:
        """단일 피드 파싱
        
        Args:
            url: RSS 피드 URL
            
        Returns:
            표준화된 뉴스 아이템 리스트
        """
        try:
            feed = feedparser.parse(url)
            
            # 파싱 에러 체크
            if feed.bozo:
                print(f"Warning: Feed has errors - {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                item = self._parse_entry(entry, url)
                if item:
                    items.append(item)
            
            return items
        
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")
            return []
    
    def _parse_entry(self, entry, source_url: str) -> Optional[dict]:
        """엔트리를 표준 형식으로 변환
        
        Args:
            entry: feedparser entry 객체
            source_url: 소스 피드 URL
            
        Returns:
            표준화된 뉴스 아이템 딕셔너리
        """
        try:
            # 필수 필드 확인
            if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                return None
            
            # ID 생성 (link 기반 해시)
            item_id = hashlib.md5(entry.link.encode()).hexdigest()
            
            # 발행 시간 파싱
            published_at = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass
            
            if not published_at:
                published_at = datetime.utcnow()
            
            # 요약 추출
            summary = None
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            
            return {
                'id': item_id,
                'title': entry.title,
                'link': entry.link,
                'summary': summary,
                'published_at': published_at,
                'source_url': source_url,
                'author': getattr(entry, 'author', None),
                'tags': [tag.term for tag in getattr(entry, 'tags', [])]
            }
        
        except Exception as e:
            print(f"Error parsing entry: {e}")
            return None
    
    def parse_all(self) -> List[dict]:
        """모든 피드 파싱
        
        Returns:
            모든 피드의 뉴스 아이템 리스트
        """
        all_items = []
        
        for url in self.feed_urls:
            items = self.parse_feed(url)
            all_items.extend(items)
        
        # 발행 시간 역순 정렬
        all_items.sort(key=lambda x: x['published_at'], reverse=True)
        
        return all_items


# 사용 예제
if __name__ == "__main__":
    feeds = [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",   # CNBC Finance
        "https://www.coindesk.com/arc/outboundfeeds/rss/",        # CoinDesk
        "https://cointelegraph.com/rss",                          # Cointelegraph
    ]

    parser = RSSFeedParser(feeds)
    items = parser.parse_all()

    print(f"Total items: {len(items)}")
    for item in items[:5]:
        print(f"\n{item['title']}")
        print(f"Published: {item['published_at']}")
        print(f"Link: {item['link']}")
```

---

## 폴링 전략

### 권장 폴링 간격

```python
# 실시간 뉴스: 1-2분
REALTIME_INTERVAL = 120  # seconds

# 일반 뉴스: 5-10분
NORMAL_INTERVAL = 300  # seconds

# 덜 중요한 피드: 15-30분
LOW_PRIORITY_INTERVAL = 900  # seconds
```

### 비동기 폴링 구현

```python
import asyncio
import aiohttp
import feedparser
from datetime import datetime

class AsyncRSSPoller:
    """비동기 RSS 폴링"""
    
    def __init__(self, feed_url: str, interval: float = 120.0):
        self.feed_url = feed_url
        self.interval = interval
        self.seen_ids = set()
    
    async def fetch_feed(self) -> str:
        """RSS 피드 가져오기 (비동기)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as response:
                return await response.text()
    
    async def poll(self):
        """폴링 루프"""
        while True:
            try:
                # 피드 가져오기
                feed_content = await self.fetch_feed()
                
                # 파싱 (동기 함수이므로 executor 사용)
                loop = asyncio.get_event_loop()
                feed = await loop.run_in_executor(
                    None, 
                    feedparser.parse, 
                    feed_content
                )
                
                # 새 아이템만 처리
                for entry in feed.entries:
                    entry_id = entry.link
                    if entry_id not in self.seen_ids:
                        self.seen_ids.add(entry_id)
                        await self.process_entry(entry)
                
            except Exception as e:
                print(f"Polling error: {e}")
            
            # 다음 폴링까지 대기
            await asyncio.sleep(self.interval)
    
    async def process_entry(self, entry):
        """새 엔트리 처리"""
        print(f"New item: {entry.title}")
        # 여기서 알림 발송 등 처리
```

---

## 에러 처리 및 모범 사례

### 1. 파싱 에러 처리

```python
import feedparser

feed = feedparser.parse(url)

# bozo 플래그 확인 (파싱 오류 감지)
if feed.bozo:
    print(f"Feed has errors: {feed.bozo_exception}")
    # 계속 진행 (일부 피드는 오류가 있어도 사용 가능)
```

### 2. 네트워크 에러 처리

```python
import requests
import feedparser

def safe_parse_feed(url: str, timeout: int = 10):
    try:
        # requests로 먼저 가져오기 (타임아웃 설정)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # feedparser로 파싱
        feed = feedparser.parse(response.content)
        return feed
    
    except requests.Timeout:
        print(f"Timeout fetching {url}")
        return None
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
```

### 3. 중복 제거

```python
class DuplicateFilter:
    """중복 뉴스 필터링"""
    
    def __init__(self, max_size: int = 10000):
        self.seen_ids = set()
        self.max_size = max_size
    
    def is_duplicate(self, item_id: str) -> bool:
        """중복 여부 확인"""
        if item_id in self.seen_ids:
            return True
        
        self.seen_ids.add(item_id)
        
        # 메모리 관리: 최대 크기 초과 시 오래된 것 제거
        if len(self.seen_ids) > self.max_size:
            # 간단한 방법: 절반 제거
            self.seen_ids = set(list(self.seen_ids)[self.max_size // 2:])
        
        return False
```

### 4. HTML 태그 제거

```python
import re
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    """HTML 태그 제거"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = []
    
    def handle_data(self, d):
        self.text.append(d)
    
    def get_data(self):
        return ''.join(self.text)

def strip_html_tags(html: str) -> str:
    """HTML 태그 제거하여 텍스트만 추출"""
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# 사용
summary = entry.summary
clean_summary = strip_html_tags(summary)
```

### 5. User-Agent 설정

일부 사이트는 User-Agent를 확인합니다:

```python
import feedparser

# User-Agent 헤더 설정
feedparser.USER_AGENT = "MyNewsBot/1.0 (myemail@example.com)"

feed = feedparser.parse(url)
```

---

## 지원하는 RSS 형식

feedparser는 다음 형식을 모두 지원합니다:

- **RSS 0.90, 0.91, 0.92, 0.93, 0.94**
- **RSS 1.0**
- **RSS 2.0**
- **Atom 0.3, 1.0**
- **CDF**

모든 형식은 동일한 인터페이스로 파싱됩니다.

---

## 제한사항 및 주의사항

### 1. 업데이트 빈도
- RSS 피드는 **실시간이 아닙니다**
- 대부분 1-5분 간격으로 업데이트
- 속보는 지연될 수 있음

### 2. Rate Limiting
- 대부분의 RSS 피드는 rate limit이 없음
- 하지만 **과도한 요청은 금지** (1-2분 간격 권장)
- 서버 부하를 고려하여 적절한 폴링 간격 설정

### 3. 피드 가용성
- 일부 사이트는 RSS 피드를 중단할 수 있음
- 정기적으로 피드 URL 확인 필요
- 404 에러 시 대체 피드 사용

### 4. 콘텐츠 품질
- 요약(summary)이 없는 경우 있음
- HTML 태그가 포함된 경우 있음
- 이미지 링크가 깨진 경우 있음

---

## 참고 자료

### 공식 문서
- [feedparser 공식 문서](https://feedparser.readthedocs.io/)
- [feedparser PyPI](https://pypi.org/project/feedparser/)
- [feedparser GitHub](https://github.com/kurtmckee/feedparser)

### RSS 피드 목록
- [CNBC RSS Feeds](https://www.cnbc.com/rss-feeds/)
- [Top Cryptocurrency RSS Feeds](https://rss.feedspot.com/cryptocurrency_news_rss_feeds/)
- [Top Business News RSS Feeds](https://rss.feedspot.com/business_news_rss_feeds/)

### 튜토리얼
- [FeedParser Guide - ScrapeOps](https://scrapeops.io/python-web-scraping-playbook/feedparser/)
- [Fetching RSS Feeds in Python](https://medium.com/@jonathanmondaut/fetching-data-from-rss-feeds-in-python-a-comprehensive-guide-a3dc86a5b7bc)

---

## 검증된 피드 요약

| 소스 | 상태 | 카테고리 | 추천 |
|------|------|----------|------|
| CNBC Top News | ✅ 활성 | 주요 뉴스 | ⭐⭐⭐ |
| CNBC Finance | ✅ 활성 | 금융/암호화폐 | ⭐⭐⭐ |
| CNBC Economy | ✅ 활성 | 경제 | ⭐⭐ |
| Bloomberg Markets | ✅ 활성 | 글로벌 시장 | ⭐⭐⭐ |
| CoinDesk | ✅ 활성 | 암호화폐 | ⭐⭐⭐ |
| Cointelegraph | ✅ 활성 | 블록체인/핀테크 | ⭐⭐⭐ |
| CNBC Crypto | ❌ 비활성 | - | - |
| Reuters | ❌ 비활성 | - | - |

---

## 업데이트 이력

- 2026-02-04: 피드 검증 및 보완
  - 각 피드 URL 실제 접속 테스트
  - CNBC Crypto 피드 404 에러 확인 → 비활성 표시
  - Reuters 공식 RSS 중단 확인 → 비권장으로 변경
  - Cointelegraph 피드 추가 (검증됨)
  - 피드별 XML 네임스페이스 및 필드 상세 정보 추가
  - 검증된 피드 요약 테이블 추가
- 2026-02-04: 초기 문서 작성
  - CNBC, Reuters, Bloomberg, CoinDesk 피드 목록
  - feedparser 기본 사용법 및 전체 구현 예제
  - 비동기 폴링 구현
  - 에러 처리 및 모범 사례
  - HTML 태그 제거, 중복 필터링 등
