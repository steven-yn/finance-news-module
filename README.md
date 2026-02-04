# Finance News

실시간 금융 뉴스 수집 및 Discord 알림 시스템

## 개요

미국 증시 및 암호화폐 관련 뉴스를 실시간으로 수집하고 Discord로 알림을 발송합니다.

### 실행 방법

source .venv/bin/activate
python -m finance_news.main

### 주요 기능

- **실시간 뉴스 수집**: WebSocket 기반 실시간 뉴스 스트림
- **다양한 소스**: Finnhub, RSS 피드, SEC EDGAR, FRED
- **필터링**: 키워드 기반 필터링 및 중복 제거
- **Discord 알림**: qfin DiscordNotifier 재사용

## 아키텍처

### 핵심 컴포넌트

- `NewsSource`: 뉴스 소스 추상 클래스
  - `WebSocketNewsSource`: WebSocket 기반 소스 베이스
  - `PollingNewsSource`: 폴링 기반 소스 베이스
- `NewsFilter`: 뉴스 필터 추상 클래스
- `NewsOrchestrator`: 여러 소스를 통합 관리

### 데이터 흐름

```
NewsSource → NewsItem → NewsFilter → NewsAlert → DiscordNotifier
```

## 설치

```bash
cd ~/projects/finance-news
pip install -e .
```

## 설정

`.env` 파일 생성:

```env
FINANCE_NEWS_FINNHUB_API_KEY=your_key
FINANCE_NEWS_FRED_API_KEY=your_key
FINANCE_NEWS_DISCORD_WEBHOOK_URL=your_webhook_url
```

## 실행

```bash
python -m finance_news.main
```

## 개발 상태

- [x] Phase 1: 핵심 아키텍처 구축
- [x] Phase 2: API 문서화 - Finnhub
- [x] Phase 3: API 문서화 - RSS 피드
- [x] Phase 4: API 문서화 - SEC EDGAR
- [x] Phase 5: API 문서화 - FRED
- [x] Phase 6: Finnhub WebSocket 뉴스 소스 구현
- [x] Phase 7: RSS 피드 뉴스 소스 구현
- [x] Phase 8: SEC EDGAR 공시 소스 구현
- [x] Phase 9: FRED 경제 지표 소스 구현
- [x] Phase 10: 필터링 및 통합 ✅ **완료!**

### 구현된 소스

| 소스 | 유형 | 상태 | 파일 |
|------|------|------|------|
| **Finnhub** | WebSocket | ✅ | `src/finance_news/sources/finnhub.py` |
| **RSS** | Polling | ✅ | `src/finance_news/sources/rss.py` |
| **SEC EDGAR** | Polling | ✅ | `src/finance_news/sources/sec.py` |
| **FRED** | Polling | ✅ | `src/finance_news/sources/fred.py` |

### 구현된 필터

| 필터 | 용도 | 파일 |
|------|------|------|
| **KeywordFilter** | 키워드 기반 필터링 (암호화폐/시장 프리셋) | `src/finance_news/filters/keyword.py` |
| **DeduplicationFilter** | 해시 기반 중복 제거 | `src/finance_news/filters/dedup.py` |
| **CategoryFilter** | 카테고리 기반 필터링 | `src/finance_news/filters/keyword.py` |
| **SourceFilter** | 소스 기반 필터링 | `src/finance_news/filters/keyword.py` |

## 의존성

- qfin (로컬 패키지)
- finnhub-python
- feedparser
- fredapi
- aiohttp
- websockets
- pydantic-settings
