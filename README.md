# Finance News

실시간 금융 뉴스 수집 및 Discord 알림 시스템

## 개요

미국 증시 및 암호화폐 관련 뉴스를 실시간으로 수집하고 Discord로 알림을 발송합니다.

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
- [ ] Phase 2-5: API 문서화
- [ ] Phase 6-9: 소스 구현
- [ ] Phase 10: 필터링 및 통합

## 의존성

- qfin (로컬 패키지)
- finnhub-python
- feedparser
- fredapi
- aiohttp
- websockets
- pydantic-settings
