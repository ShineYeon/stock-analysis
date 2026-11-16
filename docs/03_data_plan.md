# 데이터 설계와 우선순위

## 데이터 계층

데이터는 원본을 보존하는 `raw`, 분석에 맞게 정규화한 `staging`, 시점 정렬된 피처와 신호를 담는 `mart`로 분리한다.

```text
외부 API/파일 → raw (원본·중복 허용) → staging (정제·표준화) → mart (피처·신호·성과)
```

## 우선 수집 데이터

| 우선순위 | 범주 | 최소 데이터 | 목적 |
| --- | --- | --- | --- |
| P0 | 종목 기준정보 | 종목코드, 종목명, 시장, 업종, 상장 상태 | 종목 식별과 유니버스 관리 |
| P0 | 가격·유동성 | 일별 OHLCV, 거래대금, 시가총액 | 수익률·변동성·거래가능성 계산 |
| P0 | 외국인 수급 | 종목별 외국인 순매수 수량/대금, 거래대금 대비 비율, 보유비중 | 핵심 가설 검증과 심리 신호 |
| P1 | 거시 | 환율, 금리, 국채수익률, CPI, M2, 경기선행지수, 외환보유액, 뉴스심리지수 | 외국인 위험선호의 시장 환경 설명 |
| P1 | 펀더멘털 | 매출, 영업이익, 순이익, 자산·부채, EPS/BPS, PER/PBR/배당수익률 | 종목 특성과 밸류에이션 통제 |
| P2 | 이벤트 | 실적 발표일, 공시, 배당, 유상증자, 지수 편입/편출 | 급격한 수급·가격 변화 해석 |
| P2 | 글로벌 | 미국 금리·달러 지수·주요 지수·변동성 지수·반도체/원자재 지표 | 글로벌 위험요인 통제 |

## 최소 테이블 제안

| 계층 | 테이블 예시 | 주요 키 |
| --- | --- | --- |
| raw | `raw.stock_prices_daily` | `date, ticker` |
| raw | `raw.investor_trading_daily` | `date, ticker, investor_type` |
| raw | `raw.foreign_ownership_daily` | `date, ticker` |
| raw | `raw.company_fundamentals` | `report_date, ticker, account_code` |
| staging | `stg.security_master` | `ticker, effective_from` |
| staging | `stg.market_daily` | `date, ticker` |
| mart | `mart.foreign_sentiment_daily` | `date, ticker` 또는 `date, market` |
| mart | `mart.stock_signal_daily` | `as_of_date, ticker, horizon` |
| mart | `mart.signal_evaluation` | `signal_date, ticker, horizon` |

## 시점 정렬 규칙

- 가격과 수급은 장 마감 후 확정된 값만 다음 거래일 신호에 사용한다.
- 재무제표와 거시지표는 관측 기간이 아니라 **공개일**을 기준으로 조인한다.
- 수정·정정 공시와 상장폐지 종목을 보존해 생존자 편향을 피한다.
- 종목코드 변경, 액면분할, 배당 조정 여부를 명시한다.

