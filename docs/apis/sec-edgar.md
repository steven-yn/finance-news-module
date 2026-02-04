# SEC EDGAR API 문서

## 개요

SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)는 미국 증권거래위원회(SEC)의 전자 공시 시스템입니다. 

- **공식 사이트**: https://www.sec.gov
- **API 엔드포인트**: https://data.sec.gov
- **API 키**: 불필요 (무료, 인증 불필요)
- **형식**: JSON RESTful API

### 특징
- ✅ **완전 무료**: API 키 불필요
- ✅ **공식 데이터**: SEC 공식 공시 데이터
- ✅ **실시간**: 1초 이내 업데이트
- ✅ **JSON 형식**: 표준화된 RESTful API

---

## 주요 SEC 공시 유형

### Form 8-K (Current Report - 즉시 공시)
**목적**: 중요한 사건 발생 시 즉시 공개

**제출 시기**: 사건 발생 후 4 영업일 이내

**포함 내용**:
- 파산 (bankruptcy)
- 인수합병 (merger, acquisition)
- CEO/임원 변경
- 계약 체결/해지
- 신용등급 변경
- 회계법인 변경
- 자산 매각
- 기타 중요 사건

**중요도**: ★★★ (가장 시간에 민감, 시장 영향 큼)

### Form 10-Q (Quarterly Report - 분기 보고서)
**목적**: 분기별 재무 상황 공개

**제출 시기**: 분기 종료 후 40-45일 이내 (연 3회)

**포함 내용**:
- 미감사 재무제표
- 경영진 논의 및 분석 (MD&A)
- 시장 위험 정보
- 법적 절차

**중요도**: ★★ (정기적 재무 정보)

### Form 10-K (Annual Report - 연간 보고서)
**목적**: 연간 재무 상황 종합 공개

**제출 시기**: 회계연도 종료 후 60-90일 이내

**포함 내용**:
- 감사된 재무제표
- 사업 개요
- 위험 요인
- 임원 보상
- 지배구조
- 종합적인 경영 분석

**중요도**: ★★★ (가장 상세한 정보)

### Form 4 (Insider Trading Report - 내부자 거래)
**목적**: 임원, 이사, 10% 이상 주주의 주식 거래 공개

**제출 시기**: 거래 후 2 영업일 이내

**포함 내용**:
- 거래자 정보 (이름, 직위)
- 거래 유형 (매수/매도)
- 거래량 및 가격
- 거래 후 보유량

**중요도**: ★★★ (내부자의 투자 심리 파악)

> **참고**: "내부자 거래 신고"는 불법 거래가 아님. 합법적인 거래를 공개하는 것.

### Form 13F (Institutional Holdings - 기관 보유)
**목적**: 대형 기관투자자의 분기별 보유 현황 공개

**제출 시기**: 분기 종료 후 45일 이내

**대상**: $100M 이상 운용 기관 (헤지펀드, 뮤추얼펀드, 연기금 등)

**포함 내용**:
- 보유 종목 리스트
- 주식 수량 및 가치
- Put/Call 옵션 보유

**중요도**: ★★ (기관 투자자 동향 파악, 단 45일 지연)

---

## API 요구사항

### 1. User-Agent 헤더 (필수!)

SEC는 **모든 요청에 User-Agent 헤더를 요구**합니다. 이메일 주소를 포함해야 합니다.

```python
headers = {
    "User-Agent": "MyCompany admin@mycompany.com"
}
```

**형식**: `<Company Name> <Email Address>`

**예시**:
```
"Mozilla/5.0 (compatible; MyBot/1.0; +mailto:admin@example.com)"
"FinanceNews/1.0 contact@financenews.com"
```

### 2. Rate Limit

- **제한**: 초당 최대 10 요청
- **위반 시**: IP 주소가 일시적으로 차단됨
- **권장**: 초당 5-8 요청 (안전 마진)

```python
import time

# 요청 간 최소 대기 시간
MIN_DELAY = 0.12  # 120ms (초당 약 8.3 요청)

time.sleep(MIN_DELAY)
```

---

## API 엔드포인트

### 1. Submissions API (회사별 공시 목록)

특정 회사의 모든 공시 내역을 가져옵니다.

#### 엔드포인트
```
GET https://data.sec.gov/submissions/CIK{CIK}.json
```

#### CIK 형식
- 10자리 숫자 (앞에 0 채우기)
- 예시: Apple Inc. = `0000320193`

#### Python 예제
```python
import requests

def get_company_submissions(cik: str) -> dict:
    """회사 공시 내역 가져오기"""
    # CIK를 10자리로 포맷
    cik_padded = str(cik).zfill(10)
    
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    headers = {
        "User-Agent": "FinanceNews admin@example.com"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

# 사용 예제
data = get_company_submissions("320193")  # Apple
print(f"Company: {data['name']}")
print(f"Ticker: {data['tickers']}")
```

#### 응답 구조
```json
{
  "cik": "320193",
  "entityType": "operating",
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "ein": "942404110",
  "description": "...",
  "website": "https://www.apple.com",
  "investorWebsite": "https://investor.apple.com",
  "category": "Large accelerated filer",
  "fiscalYearEnd": "0930",
  "stateOfIncorporation": "CA",
  "phone": "408-996-1010",
  "filings": {
    "recent": {
      "accessionNumber": ["0000320193-24-000123", "..."],
      "filingDate": ["2024-01-31", "..."],
      "reportDate": ["2023-12-31", "..."],
      "acceptanceDateTime": ["2024-01-31T16:30:00.000Z", "..."],
      "form": ["10-Q", "8-K", "..."],
      "primaryDocument": ["aapl-20231231.htm", "..."],
      "primaryDocDescription": ["10-Q", "..."]
    },
    "files": [
      {
        "name": "CIK0000320193-submissions-001.json",
        "filingCount": 1000,
        "filingFrom": "2014-01-01",
        "filingTo": "2020-12-31"
      }
    ]
  }
}
```

#### 주요 필드
- `name`: 회사명
- `tickers`: 티커 심볼 (예: ["AAPL"])
- `exchanges`: 거래소 (예: ["Nasdaq"])
- `filings.recent`: 최근 1년 또는 최대 1,000개 공시
- `filings.files`: 추가 과거 공시 파일 목록

---

### 2. Company Facts API (회사 재무 데이터)

XBRL 형식의 재무 데이터를 가져옵니다.

#### 엔드포인트
```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json
```

#### Python 예제
```python
def get_company_facts(cik: str) -> dict:
    """회사 재무 데이터 가져오기"""
    cik_padded = str(cik).zfill(10)
    
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    headers = {
        "User-Agent": "FinanceNews admin@example.com"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()
```

---

### 3. Company Concept API (특정 항목 데이터)

특정 재무 항목(예: 매출, 순이익)의 데이터를 가져옵니다.

#### 엔드포인트
```
GET https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK}/{taxonomy}/{tag}.json
```

#### 파라미터
- `taxonomy`: 회계 기준 (보통 `us-gaap`)
- `tag`: 재무 항목 태그
  - `Revenues`: 매출
  - `NetIncomeLoss`: 순이익
  - `Assets`: 자산
  - `Liabilities`: 부채

#### Python 예제
```python
def get_company_concept(cik: str, taxonomy: str, tag: str) -> dict:
    """특정 재무 항목 데이터 가져오기"""
    cik_padded = str(cik).zfill(10)
    
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_padded}/{taxonomy}/{tag}.json"
    headers = {
        "User-Agent": "FinanceNews admin@example.com"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

# 매출 데이터 가져오기
revenues = get_company_concept("320193", "us-gaap", "Revenues")
```

---

## 전체 구현 예제

### SEC EDGAR 공시 모니터링 클래스

```python
import requests
import time
from datetime import datetime
from typing import List, Optional

class SECFilingsMonitor:
    """SEC EDGAR 공시 모니터링
    
    특정 회사들의 최근 공시를 모니터링
    """
    
    BASE_URL = "https://data.sec.gov"
    MIN_DELAY = 0.12  # 초당 8.3 요청
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.headers = {
            "User-Agent": user_agent
        }
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Rate limit 준수"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_DELAY:
            time.sleep(self.MIN_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def get_company_submissions(self, cik: str) -> Optional[dict]:
        """회사 공시 내역 가져오기"""
        self._rate_limit()
        
        cik_padded = str(cik).zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching submissions for CIK {cik}: {e}")
            return None
    
    def get_recent_filings(
        self, 
        cik: str, 
        form_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[dict]:
        """최근 공시 가져오기
        
        Args:
            cik: 회사 CIK
            form_types: 필터링할 공시 유형 (예: ["8-K", "10-Q"])
            limit: 최대 개수
            
        Returns:
            공시 리스트
        """
        data = self.get_company_submissions(cik)
        if not data:
            return []
        
        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []
        
        # 컬럼형 데이터를 행 기반으로 변환
        filings = []
        for i in range(len(recent.get("accessionNumber", []))):
            filing = {
                "accessionNumber": recent["accessionNumber"][i],
                "filingDate": recent["filingDate"][i],
                "reportDate": recent.get("reportDate", [None] * len(recent["accessionNumber"]))[i],
                "acceptanceDateTime": recent["acceptanceDateTime"][i],
                "form": recent["form"][i],
                "primaryDocument": recent["primaryDocument"][i],
                "primaryDocDescription": recent.get("primaryDocDescription", [None] * len(recent["accessionNumber"]))[i],
            }
            
            # 공시 유형 필터링
            if form_types and filing["form"] not in form_types:
                continue
            
            filings.append(filing)
            
            if len(filings) >= limit:
                break
        
        return filings
    
    def monitor_companies(
        self, 
        ciks: List[str], 
        form_types: Optional[List[str]] = None
    ) -> dict:
        """여러 회사의 최근 공시 모니터링
        
        Args:
            ciks: CIK 리스트
            form_types: 필터링할 공시 유형
            
        Returns:
            {cik: [filings]} 딕셔너리
        """
        results = {}
        
        for cik in ciks:
            filings = self.get_recent_filings(cik, form_types, limit=5)
            if filings:
                results[cik] = filings
        
        return results


# 사용 예제
if __name__ == "__main__":
    monitor = SECFilingsMonitor(
        user_agent="FinanceNews/1.0 admin@example.com"
    )
    
    # 주요 테크 기업 CIK
    companies = {
        "0000320193": "Apple",
        "0001018724": "Amazon",
        "0001652044": "Google (Alphabet)",
        "0001318605": "Tesla",
    }
    
    # 8-K (중요 사건) 공시만 모니터링
    results = monitor.monitor_companies(
        list(companies.keys()),
        form_types=["8-K"]
    )
    
    for cik, filings in results.items():
        company_name = companies[cik]
        print(f"\n{company_name} (CIK: {cik}):")
        for filing in filings:
            print(f"  - {filing['form']}: {filing['filingDate']} - {filing['primaryDocDescription']}")
```

---

### 4. Frames API (기간별 집계 데이터)

여러 회사의 특정 항목을 한 번에 집계합니다.

#### 엔드포인트
```
GET https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json
```

#### 파라미터
- `taxonomy`: 회계 기준 (예: `us-gaap`)
- `tag`: 재무 항목 태그 (예: `Revenues`)
- `unit`: 단위 (예: `USD`)
- `period`: 기간 형식
  - 연간: `CY2023` (Calendar Year 2023)
  - 분기: `CY2023Q1` (Q1 2023)
  - 순간: `CY2023Q1I` (Q1 2023 Instantaneous)

#### Python 예제
```python
def get_frames(taxonomy: str, tag: str, unit: str, period: str) -> dict:
    """기간별 집계 데이터 가져오기"""
    url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json"
    headers = {
        "User-Agent": "FinanceNews admin@example.com"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()

# 2023년 모든 회사의 매출 데이터
revenues = get_frames("us-gaap", "Revenues", "USD", "CY2023")
```

---

## RSS 피드 (실시간 공시 알림)

SEC EDGAR는 RSS/Atom 피드를 통해 실시간 공시 알림을 제공합니다.

### 최신 공시 피드
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={FORM_TYPE}&company=&owner=include&count=40&output=atom
```

### 파라미터
- `type`: 공시 유형 필터 (예: `8-K`, `10-K`, `4`)
- `company`: 회사명 검색 (선택)
- `count`: 결과 개수 (최대 100)
- `output`: `atom` 또는 `rss`

### 예시 URL
```
# 모든 8-K 공시
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom

# 모든 Form 4 (내부자 거래)
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&output=atom

# Apple 관련 모든 공시
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&company=apple&output=atom
```

### 구조화된 데이터 피드
SEC는 10분마다 업데이트되는 구조화된 RSS 피드도 제공합니다:
- 업데이트 주기: 10분 (월-금, 6am-10pm EST)
- URL: https://www.sec.gov/structureddata/rss-feeds

---

## 공시 문서 다운로드

공시 문서 URL 형식:
```
https://www.sec.gov/Archives/edgar/data/{CIK}/{AccessionNumber}/{PrimaryDocument}
```

### Python 예제

```python
def get_filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    """공시 문서 URL 생성"""
    # Accession Number에서 하이픈 제거
    accession_no_hyphens = accession_number.replace("-", "")
    
    # CIK에서 앞의 0 제거
    cik_stripped = str(int(cik))
    
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession_no_hyphens}/{primary_document}"
    return url

# 사용 예제
cik = "0000320193"
accession = "0000320193-24-000123"
document = "aapl-20231231.htm"

url = get_filing_url(cik, accession, document)
print(url)
# https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20231231.htm
```

---

## CIK 검색

### 회사명으로 CIK 찾기

SEC는 회사명 → CIK 검색 API를 제공하지 않지만, 다음 방법을 사용할 수 있습니다:

#### 방법 1: SEC 검색 페이지
```
https://www.sec.gov/cgi-bin/browse-edgar?company={COMPANY_NAME}&action=getcompany
```

#### 방법 2: CIK 매핑 JSON
SEC는 모든 회사의 CIK 매핑 파일을 제공합니다:
```
https://www.sec.gov/files/company_tickers.json
```

```python
import requests

def get_cik_mapping() -> dict:
    """모든 회사의 CIK 매핑 가져오기"""
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": "FinanceNews/1.0 admin@example.com"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # {0: {cik: 320193, ticker: "AAPL", title: "Apple Inc."}, ...}
    data = response.json()
    
    # ticker → cik 매핑 생성
    ticker_to_cik = {}
    for item in data.values():
        ticker = item.get("ticker")
        cik = str(item.get("cik_str")).zfill(10)
        ticker_to_cik[ticker] = cik
    
    return ticker_to_cik

# 사용
mapping = get_cik_mapping()
apple_cik = mapping.get("AAPL")
print(f"Apple CIK: {apple_cik}")  # 0000320193
```

---

## 에러 처리

### HTTP 에러

```python
def safe_request(url: str, headers: dict, max_retries: int = 3):
    """안전한 요청 (재시도 포함)"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print("403 Forbidden: Check User-Agent header")
                raise
            elif e.response.status_code == 429:
                print("429 Too Many Requests: Rate limit exceeded")
                time.sleep(2 ** attempt)  # 지수 백오프
            else:
                print(f"HTTP Error: {e}")
                raise
        
        except requests.Timeout:
            print(f"Timeout (attempt {attempt + 1}/{max_retries})")
            time.sleep(1)
        
        except requests.RequestException as e:
            print(f"Request error: {e}")
            raise
    
    return None
```

---

## 주의사항

### 1. User-Agent 필수
- User-Agent 헤더가 없으면 **403 Forbidden** 에러
- 반드시 이메일 주소 포함

### 2. Rate Limit 준수
- 초당 10 요청 초과 시 IP 차단
- 여러 머신에서 요청해도 총합으로 계산됨

### 3. CIK 형식
- 10자리 숫자 (앞에 0 채우기)
- 잘못된 형식: `320193` ❌
- 올바른 형식: `0000320193` ✅

### 4. 데이터 지연
- 일반적으로 1초 이내 업데이트
- 실시간이지만 약간의 지연 가능

---

## 참고 자료

### 공식 문서
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [SEC Rate Control Limits](https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits)
- [API Overview PDF](https://www.sec.gov/files/edgar/filer-information/api-overview.pdf)

### SEC 공시 유형
- [Form 10-K](https://www.investor.gov/introduction-investing/investing-basics/glossary/form-10-k)
- [SEC Filing Types Guide](https://www.toppanmerrill.com/blog/how-to-navigate-forms-10-k-10-q-20-f-40-f-8-k-and-6-k/)

### Python 라이브러리
- [sec-edgar-api (PyPI)](https://pypi.org/project/sec-edgar-api/)
- [sec-edgar-api Documentation](https://sec-edgar-api.readthedocs.io/)

### 튜토리얼
- [Introduction to EDGAR API](https://www.thefullstackaccountant.com/blog/intro-to-edgar)
- [EDGAR API Guide](https://daloopa.com/blog/analyst-best-practices/comprehensive-guide-to-sec-edgar-api-and-database)

---

## sec-edgar-api 라이브러리 사용

공식 래퍼 라이브러리를 사용하면 더 쉽게 API를 호출할 수 있습니다.

### 설치
```bash
pip install sec-edgar-api
```

### 사용 예제
```python
from sec_edgar_api import EdgarClient

# User-Agent 필수
edgar = EdgarClient(user_agent="FinanceNews admin@example.com")

# 회사 공시 내역 (자동 페이지네이션)
submissions = edgar.get_submissions(cik="320193")

# 회사 재무 데이터
facts = edgar.get_company_facts(cik="320193")

# 특정 재무 항목
revenues = edgar.get_company_concept(
    cik="320193",
    taxonomy="us-gaap",
    tag="Revenues"
)

# 기간별 집계
frames = edgar.get_frames(
    taxonomy="us-gaap",
    tag="Revenues",
    unit="USD",
    year="2023"
)
```

### 주요 기능
- 자동 Rate Limiting (10 requests/second)
- 자동 페이지네이션 처리
- Type Hints 지원

---

## 공시 유형 요약

| Form | 이름 | 제출 시기 | 중요도 | 용도 |
|------|------|----------|--------|------|
| **8-K** | Current Report | 4일 이내 | ★★★ | 중요 사건 즉시 공시 |
| **10-K** | Annual Report | 60-90일 | ★★★ | 연간 종합 보고서 |
| **10-Q** | Quarterly Report | 40-45일 | ★★ | 분기 재무 보고서 |
| **Form 4** | Insider Trading | 2일 이내 | ★★★ | 내부자 주식 거래 |
| **13F** | Holdings Report | 45일 | ★★ | 기관 보유 현황 |

---

## 업데이트 이력

- 2026-02-04: 문서 검증 및 보완
  - Form 4 (내부자 거래), Form 13F (기관 보유) 추가
  - Frames API 추가
  - RSS 피드 옵션 추가
  - sec-edgar-api 라이브러리 사용법 추가
  - 공시 유형 요약 테이블 추가
- 2026-02-04: 초기 문서 작성
  - Submissions, Company Facts, Company Concept API
  - SEC 공시 유형 (8-K, 10-Q, 10-K) 설명
  - User-Agent 요구사항 및 Rate Limit
  - 전체 구현 예제 (SECFilingsMonitor)
  - CIK 검색 및 매핑
  - 에러 처리 및 주의사항
