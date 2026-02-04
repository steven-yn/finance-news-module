# Finnhub API 문서

## 개요

Finnhub는 실시간 주식, 외환, 암호화폐 데이터를 제공하는 무료 API입니다. WebSocket과 REST API를 모두 지원합니다.

- **공식 문서**: https://finnhub.io/docs/api
- **WebSocket 문서**: https://finnhub.io/docs/api/websocket-trades
- **뉴스 WebSocket**: https://finnhub.io/docs/api/websocket-news

## 인증

모든 API 요청에는 API 키가 필요합니다.

### API 키 발급
1. https://finnhub.io/register 에서 무료 계정 생성
2. 대시보드에서 API 키 확인

### 인증 방법

**WebSocket**:
```
wss://ws.finnhub.io?token={API_KEY}
```

**REST API**:
```
헤더: X-Finnhub-Token: {API_KEY}
또는
쿼리 파라미터: ?token={API_KEY}
```

---

## WebSocket API

### 1. 연결

```python
import websocket

ws = websocket.WebSocketApp(
    "wss://ws.finnhub.io?token={API_KEY}",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)
ws.on_open = on_open
ws.run_forever()
```

### 2. 구독 (Subscribe)

#### 거래 데이터 (Trades)
```json
{"type": "subscribe", "symbol": "AAPL"}
{"type": "subscribe", "symbol": "BINANCE:BTCUSDT"}
{"type": "subscribe", "symbol": "CRYPTO:BTC"}
```

#### 뉴스/프레스 릴리스
```json
{"type": "subscribe-news", "symbol": "AAPL"}
{"type": "subscribe-news", "symbol": "CRYPTO:BTC"}
```

### 3. 구독 해제 (Unsubscribe)
```json
{"type": "unsubscribe", "symbol": "AAPL"}
{"type": "unsubscribe-news", "symbol": "AAPL"}
```

### 4. 메시지 형식

#### Ping 메시지 (서버 → 클라이언트)
```json
{"type": "ping"}
```

클라이언트는 주기적으로 ping에 응답해야 연결 유지됩니다.

#### 거래 데이터 메시지
```json
{
  "type": "trade",
  "data": [
    {
      "s": "AAPL",      // 심볼
      "p": 150.25,      // 가격
      "v": 100,         // 거래량
      "t": 1234567890,  // 타임스탬프 (milliseconds)
      "c": ["12", "37"] // 거래 조건 코드
    }
  ]
}
```

#### 뉴스 메시지 (추정 형식)
```json
{
  "type": "news",
  "data": [
    {
      "id": 123456,
      "headline": "Bitcoin reaches new high",
      "summary": "Bitcoin price surges...",
      "source": "Reuters",
      "url": "https://...",
      "datetime": 1234567890,
      "category": "crypto",
      "related": ["CRYPTO:BTC"]
    }
  ]
}
```

*주의: 뉴스 메시지의 정확한 형식은 공식 문서에서 확인 필요*

### 5. 암호화폐 심볼 형식

Finnhub에서 암호화폐는 두 가지 형식을 지원합니다:

1. **거래소 프리픽스**: `{EXCHANGE}:{PAIR}`
   - `BINANCE:BTCUSDT`
   - `COINBASE:BTCUSD`
   - `KRAKEN:ETHUSD`

2. **일반 암호화폐**: `CRYPTO:{SYMBOL}`
   - `CRYPTO:BTC`
   - `CRYPTO:ETH`
   - `CRYPTO:SOL`

---

## REST API

### 1. 회사 뉴스 (Company News)

북미 기업의 최근 1년 뉴스를 가져옵니다.

#### 엔드포인트
```
GET /api/v1/company-news
```

#### 파라미터
- `symbol` (required): 주식 심볼 (예: AAPL, TSLA)
- `from` (required): 시작 날짜 (YYYY-MM-DD)
- `to` (required): 종료 날짜 (YYYY-MM-DD)

#### Python 예제
```python
import finnhub

finnhub_client = finnhub.Client(api_key="YOUR_API_KEY")
news = finnhub_client.company_news('AAPL', _from="2024-01-01", to="2024-01-31")
```

#### 응답 형식
```json
[
  {
    "category": "company news",
    "datetime": 1234567890,
    "headline": "Apple announces new product",
    "id": 123456,
    "image": "https://...",
    "related": "AAPL",
    "source": "Reuters",
    "summary": "Apple Inc. announced...",
    "url": "https://..."
  }
]
```

### 2. 일반 뉴스 (Market News)

카테고리별 시장 뉴스를 가져옵니다.

#### 엔드포인트
```
GET /api/v1/news
```

#### 파라미터
- `category` (required): 뉴스 카테고리
  - `general`: 일반 뉴스
  - `forex`: 외환 뉴스
  - `crypto`: 암호화폐 뉴스
  - `merger`: M&A 뉴스

#### Python 예제
```python
crypto_news = finnhub_client.general_news('crypto', min_id=0)
```

#### 응답 형식
```json
[
  {
    "category": "crypto",
    "datetime": 1234567890,
    "headline": "Bitcoin surges to new high",
    "id": 789012,
    "image": "https://...",
    "related": "",
    "source": "CoinDesk",
    "summary": "Bitcoin price reaches...",
    "url": "https://..."
  }
]
```

---

## Rate Limits

### 무료 플랜 (Free Tier)
- **API 호출**: 60 calls/minute
- **WebSocket 연결**: 1 connection
- **WebSocket 메시지**: Unlimited (단, 연결당 제한 있음)

### 프리미엄 플랜
- 더 높은 rate limit
- 여러 WebSocket 연결 지원
- 실시간 데이터 지연 감소

*최신 정보는 https://finnhub.io/pricing 참조*

---

## 에러 처리

### WebSocket 에러

#### 연결 끊김
```python
def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: {close_status_code} - {close_msg}")
    # 재연결 로직 구현
```

#### 에러 핸들링
```python
def on_error(ws, error):
    print(f"Error: {error}")
    # 에러 로깅 및 복구 로직
```

### 재연결 전략

**지수 백오프 (Exponential Backoff)**:
```python
import time

MAX_RETRIES = 10
BASE_DELAY = 1  # 초

def connect_with_retry(url):
    for retry in range(MAX_RETRIES):
        try:
            ws = websocket.create_connection(url)
            return ws
        except Exception as e:
            delay = min(BASE_DELAY * (2 ** retry), 60)
            print(f"Retry {retry+1}/{MAX_RETRIES} in {delay}s")
            time.sleep(delay)
    
    raise Exception("Max retries exceeded")
```

---

## 구현 시 주의사항

### 1. Ping/Pong 처리
- 서버가 주기적으로 `{"type":"ping"}` 전송
- 클라이언트는 연결 유지를 위해 응답 필요 (자동 처리됨)
- WebSocket 라이브러리가 자동으로 처리하지만, 커스텀 핸들러 구현 가능

### 2. 심볼 형식 확인
- 암호화폐: `CRYPTO:BTC` 또는 `BINANCE:BTCUSDT`
- 주식: `AAPL`, `TSLA` (거래소 없음)
- 외환: `IC MARKETS:1`

### 3. 메시지 파싱
- JSON 파싱 에러 처리 필수
- 알 수 없는 메시지 타입 무시
- `data` 필드가 배열인 경우 주의

### 4. 중복 메시지
- 네트워크 이슈로 중복 메시지 수신 가능
- 클라이언트에서 중복 제거 로직 필요 (ID 기반)

---

## 전체 구현 예제

### Python WebSocket 클라이언트

```python
import json
import websocket
import logging

logger = logging.getLogger(__name__)

class FinnhubWebSocketClient:
    def __init__(self, api_key, symbols):
        self.api_key = api_key
        self.symbols = symbols
        self.url = f"wss://ws.finnhub.io?token={api_key}"
        self.ws = None
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "ping":
                logger.debug("Received ping")
            elif msg_type == "trade":
                self.handle_trade(data.get("data", []))
            elif msg_type == "news":
                self.handle_news(data.get("data", []))
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
    
    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"Connection closed: {close_status_code} - {close_msg}")
    
    def on_open(self, ws):
        logger.info("Connection opened")
        for symbol in self.symbols:
            subscribe_msg = json.dumps({
                "type": "subscribe-news",
                "symbol": symbol
            })
            ws.send(subscribe_msg)
            logger.info(f"Subscribed to {symbol}")
    
    def handle_trade(self, trades):
        for trade in trades:
            logger.info(f"Trade: {trade}")
    
    def handle_news(self, news_items):
        for news in news_items:
            logger.info(f"News: {news.get('headline')}")
    
    def connect(self):
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        self.ws.run_forever()

# 사용 예제
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    client = FinnhubWebSocketClient(
        api_key="YOUR_API_KEY",
        symbols=["CRYPTO:BTC", "CRYPTO:ETH", "AAPL"]
    )
    
    client.connect()
```

---

## 참고 자료

### 공식 문서
- [Finnhub API 문서](https://finnhub.io/docs/api)
- [WebSocket Trades 문서](https://finnhub.io/docs/api/websocket-trades)
- [WebSocket News 문서](https://finnhub.io/docs/api/websocket-news)
- [Pricing 정보](https://finnhub.io/pricing)

### 예제 코드
- [Elastic Tutorials - Finnhub WebSocket](https://github.com/elastic/tutorials/blob/master/websockets-finnhub/finnhub-websockets.py)
- [Finnhub Python SDK](https://github.com/Finnhub-Stock-API/finnhub-python)

### 관련 기사
- [Finnhub API Tutorial - Analyzing Alpha](https://analyzingalpha.com/finnhub-api-python-tutorial)
- [IBKR Campus - Exploring Finnhub.io API](https://www.interactivebrokers.com/campus/ibkr-quant-news/exploring-the-finnhub-io-api/)

---

## 업데이트 이력

- 2026-02-04: 초기 문서 작성
  - WebSocket API 연결 및 구독 방법
  - REST API 엔드포인트
  - Rate limits 및 에러 처리
  - 전체 구현 예제
