# FRED API 문서

## 개요

FRED (Federal Reserve Economic Data)는 미국 연방준비제도 세인트루이스 은행이 제공하는 경제 데이터베이스입니다.

- **공식 사이트**: https://fred.stlouisfed.org/
- **API 문서**: https://fred.stlouisfed.org/docs/api/fred/
- **API 키 발급**: https://fred.stlouisfed.org/docs/api/api_key.html
- **형식**: RESTful API (JSON, XML)

### 특징
- ✅ **무료**: 무료 API 키 발급
- ✅ **방대한 데이터**: 80만+ 경제 시계열 데이터
- ✅ **신뢰성**: 미국 연방준비제도 공식 데이터
- ✅ **과거 수정본**: ALFRED를 통한 데이터 리비전 추적

---

## 주요 경제 지표

### 1. 연방기금금리 (Federal Funds Rate)
**Series ID**: `DFF` (일일), `FEDFUNDS` (월별)

**설명**: 미국 중앙은행의 기준금리. 통화정책의 핵심 지표.

**영향**: 
- 금리 인상 → 달러 강세, 주식 하락 가능
- 금리 인하 → 달러 약세, 주식 상승 가능

**발표**: 매일 (일일), 매월 (월별)

### 2. 소비자물가지수 (Consumer Price Index)
**Series ID**: `CPIAUCSL` (전체), `CPILFESL` (근원)

**설명**: 인플레이션 측정 지표. 모든 도시 소비자 대상.

**영향**:
- 높은 CPI → 금리 인상 압박
- 낮은 CPI → 금리 인하 가능성

**발표**: 매월 중순 (전월 데이터)

### 3. 실업률 (Unemployment Rate)
**Series ID**: `UNRATE`

**설명**: 노동시장 건강도 지표. 실업자 비율.

**영향**:
- 높은 실업률 → 경기 침체 신호
- 낮은 실업률 → 경기 호황 신호

**발표**: 매월 첫 금요일

### 4. GDP (Gross Domestic Product)
**Series ID**: `GDP` (명목), `GDPC1` (실질)

**설명**: 국내총생산. 경제 전체 규모 측정.

**영향**:
- GDP 성장 → 경제 호황
- GDP 감소 → 경기 침체

**발표**: 분기별 (3개월 후 발표, 이후 수정)

### 5. 기타 중요 지표

| Series ID | 지표명 | 설명 |
|-----------|--------|------|
| `M2SL` | 통화량 M2 | 통화 공급량 |
| `DEXUSEU` | USD/EUR 환율 | 달러-유로 환율 |
| `DCOILWTICO` | WTI 원유 | 서부텍사스유 가격 |
| `GOLDAMGBD228NLBM` | 금 가격 | 런던 금 시세 |
| `VIXCLS` | VIX 지수 | 시장 변동성 지표 |
| `T10Y2Y` | 국채 스프레드 | 10년-2년 국채 금리차 (경기 침체 신호) |

---

## API 인증

### API 키 발급

1. https://fred.stlouisfed.org/ 회원가입
2. https://fredaccount.stlouisfed.org/apikeys 접속
3. "Request API Key" 클릭
4. 32자리 영숫자 키 발급 (즉시)

### Rate Limit

- **제한**: **분당 120 요청**
- **초과 시**: HTTP 429 에러 반환
- **권장**: 분당 100 요청 이하 유지

```python
import time

# 분당 100 요청 (안전 마진)
REQUESTS_PER_MINUTE = 100
DELAY = 60.0 / REQUESTS_PER_MINUTE  # 0.6초

time.sleep(DELAY)
```

---

## Python fredapi 라이브러리

### 설치

```bash
pip install fredapi
```

### 기본 사용법

```python
from fredapi import Fred

# API 키로 클라이언트 생성
fred = Fred(api_key='your_32_character_api_key')

# 시계열 데이터 가져오기
data = fred.get_series('DFF')  # 연방기금금리

print(data.head())
# 날짜를 인덱스로 하는 pandas Series 반환
```

---

## 주요 메서드

### 1. get_series() - 시계열 데이터 가져오기

```python
# 기본 사용
unemployment = fred.get_series('UNRATE')

# 날짜 범위 지정
cpi = fred.get_series(
    'CPIAUCSL',
    observation_start='2020-01-01',
    observation_end='2024-12-31'
)

# 빈도 변경 (월별 → 분기별)
gdp_quarterly = fred.get_series(
    'GDP',
    frequency='q',  # d=일, w=주, m=월, q=분기, a=연
    aggregation_method='avg'  # avg, sum, eop
)
```

**반환**: pandas Series (날짜 인덱스, 값)

### 2. get_series_info() - 시계열 메타데이터

```python
info = fred.get_series_info('UNRATE')

print(f"Title: {info['title']}")
print(f"Units: {info['units']}")
print(f"Frequency: {info['frequency']}")
print(f"Seasonal Adj: {info['seasonal_adjustment']}")
```

**출력 예시**:
```
Title: Unemployment Rate
Units: Percent
Frequency: Monthly
Seasonal Adj: Seasonally Adjusted
```

### 3. search() - 시계열 검색

```python
# 키워드로 검색
results = fred.search('inflation', limit=10)

print(results[['id', 'title', 'frequency']])
```

**반환**: pandas DataFrame

### 4. search_by_release() - 릴리스별 검색

```python
# Employment Situation 릴리스(175)에서 검색
employment_series = fred.search_by_release(
    175,
    limit=10,
    order_by='popularity',
    sort_order='desc'
)
```

### 5. search_by_category() - 카테고리별 검색

```python
# Money, Banking, & Finance 카테고리(32991)
banking_series = fred.search_by_category(32991, limit=20)
```

### 6. get_series_latest_release() - 최신 값 가져오기

```python
# 최신 실업률
latest = fred.get_series_latest_release('UNRATE')
print(f"Latest unemployment: {latest.iloc[-1]}%")
```

---

## ALFRED - 과거 리비전 추적

많은 경제 지표는 발표 후 여러 차례 수정됩니다. ALFRED는 이런 리비전을 추적합니다.

### Vintage Date 개념

각 관측값은 3개의 날짜를 가집니다:
- **date**: 실제 날짜 (예: 2014-03-31)
- **realtime_start**: 이 값이 처음 발표된 날짜
- **realtime_end**: 이 값이 마지막으로 유효한 날짜

### get_series_all_releases() - 모든 리비전 가져오기

```python
# GDP의 모든 리비전
all_releases = fred.get_series_all_releases('GDP')

# 특정 날짜의 GDP 값 (해당 시점에 알려진 값)
vintage_data = fred.get_series_as_of_date(
    'GDP',
    '2014-05-01'
)
```

**예시**: GDP 2014 Q1
- 2014-04-30 발표: 17149.6
- 2014-05-29 수정: 17101.3 (하향)
- 2014-06-25 수정: 17016.0 (추가 하향)

---

## 릴리스 스케줄 확인

### get_series_release() - 시계열의 릴리스 정보

```python
release_info = fred.get_series_release('UNRATE')

print(f"Release ID: {release_info['id']}")
print(f"Release Name: {release_info['name']}")
print(f"Press Release: {release_info['press_release']}")
```

### get_release_dates() - 릴리스 일정

```python
# Employment Situation 릴리스 일정
release_dates = fred.get_release_dates(
    175,
    include_release_dates_with_no_data=False
)

# 다음 발표일
next_release = release_dates[release_dates > pd.Timestamp.now()].iloc[0]
print(f"Next release: {next_release}")
```

---

## 주요 릴리스 ID

| Release ID | 릴리스 이름 | 주요 지표 |
|------------|------------|----------|
| **175** | Employment Situation | UNRATE, PAYEMS (고용 지표) |
| **10** | Consumer Price Index | CPIAUCSL, CPILFESL (물가 지표) |
| **53** | Gross Domestic Product | GDP, GDPC1 (경제 성장) |
| **19** | H.15 Selected Interest Rates | DFF, FEDFUNDS (금리) |
| **18** | H.6 Money Stock Measures | M2SL (통화량) |
| **21** | H.4.1 Federal Reserve Balance Sheet | WALCL (연준 자산) |

---

## 경제 캘린더 API (REST)

### fred/releases/dates - 모든 릴리스 일정

```
GET https://api.stlouisfed.org/fred/releases/dates
    ?api_key={API_KEY}
    &file_type=json
    &include_release_dates_with_no_data=true
```

#### 파라미터
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `realtime_start` | 올해 1월 1일 | 시작 날짜 |
| `realtime_end` | 9999-12-31 | 종료 날짜 |
| `limit` | 1000 | 최대 개수 (1-1000) |
| `order_by` | release_date | 정렬 기준 |
| `include_release_dates_with_no_data` | false | 미래 일정 포함 여부 |

#### Python 예제
```python
import requests

def get_upcoming_releases(api_key: str, days: int = 7) -> list:
    """다가오는 경제 지표 발표 일정"""
    from datetime import datetime, timedelta

    url = "https://api.stlouisfed.org/fred/releases/dates"
    params = {
        'api_key': api_key,
        'file_type': 'json',
        'realtime_start': datetime.now().strftime('%Y-%m-%d'),
        'realtime_end': (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d'),
        'include_release_dates_with_no_data': 'true',
        'limit': 100
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    return data.get('release_dates', [])

# 사용 예제
releases = get_upcoming_releases('your_api_key', days=14)
for release in releases:
    print(f"{release['date']}: {release['release_name']}")
```

> **참고**: 릴리스 일정은 데이터 소스에서 발표한 예정일이며, 실제 FRED 웹사이트에 데이터가 올라오는 시점과 다를 수 있습니다.

---

## 데이터 변환 (Units)

`units` 파라미터로 데이터를 변환할 수 있습니다:

| units | 설명 | 수식 |
|-------|------|------|
| `lin` | 원본 값 (기본값) | Xt |
| `chg` | 전기 대비 변화 | Xt - Xt-1 |
| `ch1` | 전년 동기 대비 변화 | Xt - Xt-n |
| `pch` | 전기 대비 변화율 (%) | ((Xt - Xt-1) / Xt-1) × 100 |
| `pc1` | 전년 동기 대비 변화율 (%) | ((Xt - Xt-n) / Xt-n) × 100 |
| `pca` | 연율화 변화율 (%) | 복리 연율화 |
| `cch` | 복리 변화 | 연속 복리 |
| `log` | 자연로그 | ln(Xt) |

```python
# 전년 동기 대비 CPI 변화율 (인플레이션)
cpi_inflation = fred.get_series('CPIAUCSL', units='pc1')
```

---

## 전체 구현 예제

### 경제 지표 모니터링 클래스

```python
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class EconomicIndicatorMonitor:
    """FRED 경제 지표 모니터링
    
    주요 경제 지표의 최신 값과 변화를 추적
    """
    
    # 주요 지표 정의
    KEY_INDICATORS = {
        'DFF': {
            'name': 'Federal Funds Rate',
            'unit': '%',
            'importance': 'critical'
        },
        'CPIAUCSL': {
            'name': 'Consumer Price Index',
            'unit': 'Index',
            'importance': 'critical'
        },
        'UNRATE': {
            'name': 'Unemployment Rate',
            'unit': '%',
            'importance': 'critical'
        },
        'GDP': {
            'name': 'Gross Domestic Product',
            'unit': 'Billions',
            'importance': 'high'
        },
        'M2SL': {
            'name': 'M2 Money Supply',
            'unit': 'Billions',
            'importance': 'medium'
        }
    }
    
    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)
    
    def get_latest_value(self, series_id: str) -> Optional[Dict]:
        """최신 값 가져오기
        
        Args:
            series_id: FRED 시계열 ID
            
        Returns:
            {'date': date, 'value': float, 'change': float}
        """
        try:
            # 최근 3개월 데이터 (최신 값 + 이전 값)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            data = self.fred.get_series(
                series_id,
                observation_start=start_date.strftime('%Y-%m-%d'),
                observation_end=end_date.strftime('%Y-%m-%d')
            )
            
            if len(data) < 2:
                return None
            
            latest_value = data.iloc[-1]
            previous_value = data.iloc[-2]
            change = latest_value - previous_value
            change_percent = (change / previous_value) * 100 if previous_value != 0 else 0
            
            return {
                'series_id': series_id,
                'date': data.index[-1].strftime('%Y-%m-%d'),
                'value': latest_value,
                'previous_value': previous_value,
                'change': change,
                'change_percent': change_percent
            }
        
        except Exception as e:
            print(f"Error fetching {series_id}: {e}")
            return None
    
    def get_all_indicators(self) -> List[Dict]:
        """모든 주요 지표의 최신 값 가져오기"""
        results = []
        
        for series_id, info in self.KEY_INDICATORS.items():
            latest = self.get_latest_value(series_id)
            if latest:
                latest.update(info)
                results.append(latest)
        
        return results
    
    def check_significant_changes(
        self, 
        threshold_percent: float = 1.0
    ) -> List[Dict]:
        """중요한 변화가 있는 지표 찾기
        
        Args:
            threshold_percent: 변화율 임계값 (%)
            
        Returns:
            중요한 변화가 있는 지표 리스트
        """
        indicators = self.get_all_indicators()
        significant = []
        
        for indicator in indicators:
            if abs(indicator['change_percent']) >= threshold_percent:
                significant.append(indicator)
        
        return significant
    
    def format_indicator(self, indicator: Dict) -> str:
        """지표를 읽기 쉬운 형식으로 포맷"""
        name = indicator['name']
        value = indicator['value']
        unit = indicator['unit']
        change = indicator['change']
        change_pct = indicator['change_percent']
        date = indicator['date']
        
        change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        return (
            f"{change_symbol} **{name}**\n"
            f"  Current: {value:.2f} {unit}\n"
            f"  Change: {change:+.2f} ({change_pct:+.2f}%)\n"
            f"  Date: {date}"
        )
    
    def get_next_release_date(self, series_id: str) -> Optional[str]:
        """다음 발표 일정 확인"""
        try:
            # 시계열의 릴리스 정보
            release = self.fred.get_series_release(series_id)
            release_id = release['id']
            
            # 릴리스 일정
            dates = self.fred.get_release_dates(
                release_id,
                include_release_dates_with_no_data=False
            )
            
            # 미래 날짜만 필터링
            future_dates = dates[dates > pd.Timestamp.now()]
            
            if len(future_dates) > 0:
                return future_dates.iloc[0].strftime('%Y-%m-%d')
            
            return None
        
        except Exception as e:
            print(f"Error getting release date for {series_id}: {e}")
            return None


# 사용 예제
if __name__ == "__main__":
    monitor = EconomicIndicatorMonitor(api_key='your_api_key')
    
    # 모든 주요 지표 확인
    print("=== 주요 경제 지표 ===\n")
    indicators = monitor.get_all_indicators()
    for indicator in indicators:
        print(monitor.format_indicator(indicator))
        print()
    
    # 중요한 변화 확인
    print("\n=== 중요한 변화 (1% 이상) ===\n")
    significant = monitor.check_significant_changes(threshold_percent=1.0)
    for indicator in significant:
        print(monitor.format_indicator(indicator))
        print()
    
    # 다음 발표 일정
    print("\n=== 다음 발표 일정 ===\n")
    for series_id, info in monitor.KEY_INDICATORS.items():
        next_date = monitor.get_next_release_date(series_id)
        if next_date:
            print(f"{info['name']}: {next_date}")
```

---

## REST API 직접 사용

fredapi 없이 직접 REST API를 호출할 수도 있습니다.

### 엔드포인트

```
GET https://api.stlouisfed.org/fred/series/observations
```

### 파라미터

- `series_id`: 시계열 ID (필수)
- `api_key`: API 키 (필수)
- `file_type`: json, xml (기본값: xml)
- `observation_start`: 시작 날짜 (YYYY-MM-DD)
- `observation_end`: 종료 날짜 (YYYY-MM-DD)

### Python 예제

```python
import requests

def get_fred_series(series_id: str, api_key: str) -> dict:
    """FRED 시계열 데이터 가져오기 (REST API 직접 호출)"""
    url = "https://api.stlouisfed.org/fred/series/observations"
    
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json'
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()

# 사용
data = get_fred_series('DFF', 'your_api_key')
observations = data['observations']

for obs in observations[-5:]:  # 최근 5개
    print(f"{obs['date']}: {obs['value']}")
```

---

## 에러 처리

### Rate Limit 초과

```python
import time
from fredapi import Fred

def safe_get_series(fred: Fred, series_id: str, max_retries: int = 3):
    """Rate limit을 고려한 안전한 요청"""
    for attempt in range(max_retries):
        try:
            return fred.get_series(series_id)
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = (2 ** attempt) * 60  # 1분, 2분, 4분
                print(f"Rate limit exceeded. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception("Max retries exceeded")
```

### 시계열 없음

```python
try:
    data = fred.get_series('INVALID_SERIES_ID')
except Exception as e:
    if "400" in str(e):
        print("Series not found")
    else:
        print(f"Error: {e}")
```

---

## 주의사항

### 1. 데이터 리비전
- 많은 경제 지표는 발표 후 수정됨
- GDP는 3번 수정됨 (preliminary, revised, final)
- 과거 데이터와 비교 시 리비전 고려 필요

### 2. 발표 일정
- 대부분 지표는 **전월/전분기 데이터**를 발표
- 실업률: 매월 첫 금요일 (전월 데이터)
- GDP: 분기 종료 후 약 1개월 (preliminary)

### 3. 계절 조정
- `SA` = Seasonally Adjusted (계절 조정)
- `NSA` = Not Seasonally Adjusted (미조정)
- 대부분 SA 버전 사용 권장

### 4. Frequency
- 일일(d), 주간(w), 월간(m), 분기(q), 연간(a)
- 시계열마다 원본 빈도가 다름
- `frequency` 파라미터로 변환 가능

---

## 참고 자료

### 공식 문서
- [FRED API 문서](https://fred.stlouisfed.org/docs/api/fred/)
- [API 키 발급](https://fred.stlouisfed.org/docs/api/api_key.html)
- [ALFRED 문서](https://alfred.stlouisfed.org/)

### Python 라이브러리
- [fredapi PyPI](https://pypi.org/project/fredapi/)
- [fredapi GitHub](https://github.com/mortada/fredapi)
- [fredapi 사용 예제](https://mortada.net/python-api-for-fred.html)

### 튜토리얼
- [FRED API with Python](https://medium.com/@tim.dev/unlocking-fred-data-pythons-gateway-to-key-economic-insights-a4d0d1ddcbdb)
- [Streamlining Macroeconomic Data](https://medium.com/@jgbilsel/streamlining-your-macroeconomic-data-through-the-fred-api-python-52d89eff0262)

### 경제 지표 설명
- [Federal Reserve Economic Data](https://fred.stlouisfed.org/)
- [FRED Categories](https://fred.stlouisfed.org/categories)

---

## API 엔드포인트 요약

| 엔드포인트 | 용도 |
|-----------|------|
| `fred/series/observations` | 시계열 데이터 조회 |
| `fred/series` | 시계열 메타데이터 |
| `fred/series/search` | 키워드 검색 |
| `fred/releases/dates` | 모든 릴리스 일정 |
| `fred/release/dates` | 특정 릴리스 일정 |
| `fred/release/series` | 릴리스에 포함된 시계열 |

---

## 구현 상태

✅ **Phase 9 완료** (2026-02-04)
- `FREDSource` 클래스 구현 (`src/finance_news/sources/fred.py`)
- PollingNewsSource 상속, 변화 감지 방식
- 주요 지표 지원: DFF, CPIAUCSL, UNRATE, GDP, M2SL, VIXCLS, T10Y2Y
- fredapi 동기 라이브러리를 비동기로 래핑
- 중요도 기반 카테고리 분류
- 단위 테스트 및 통합 테스트 완료

---

## 업데이트 이력

- 2026-02-04: **Phase 9 - FRED 소스 구현 완료**
  - FREDSource 클래스 구현 및 테스트
  - 변화 감지 기반 알림 (임계값 0.1%)
  - 7개 주요 경제 지표 모니터링
  - 동기 API의 비동기 래핑
- 2026-02-04: 문서 검증 및 보완
  - 주요 릴리스 ID 테이블 추가
  - 경제 캘린더 API (fred/releases/dates) 추가
  - 데이터 변환 units 파라미터 상세 설명 추가
  - API 엔드포인트 요약 테이블 추가
- 2026-02-04: 초기 문서 작성
  - 주요 경제 지표 (DFF, CPIAUCSL, UNRATE, GDP 등)
  - fredapi 라이브러리 사용법
  - 시계열 데이터 가져오기 및 검색
  - ALFRED 리비전 추적
  - 릴리스 스케줄 확인
  - 전체 구현 예제 (EconomicIndicatorMonitor)
  - REST API 직접 호출
  - 에러 처리 및 주의사항
