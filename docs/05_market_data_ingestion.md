# KRX 시장 데이터 수집

`pipeline/fetch_market_data.py`는 KRX 데이터를 기반으로 특정 거래일·시장에 대해 다음을 적재한다.

- `raw.stock_prices_daily`: OHLCV, 거래대금, 시가총액, 상장주식수
- `raw.foreign_ownership_daily`: 외국인 보유수량, 지분율, 한도 및 한도소진율

`--sync-security-master` 옵션을 함께 주면 `raw.security_master`의 티커, 종목명, 시장 정보도 갱신한다. 이 작업은 종목별 이름을 조회하므로 매일 실행하지 않고 최초 적재와 정기 점검 때만 실행한다.

## 최초 준비

```powershell
python -m pip install -r requirements.txt
psql -d stock_analysis -f db/init_schema.sql
psql -d stock_analysis -f db/migrations/001_create_market_data_tables.sql
```

`.env`에는 PostgreSQL 접속 정보와 KRX Data Marketplace 로그인 정보가 있어야 한다. `pykrx`의 KRX 조회는 로그인 세션을 요구하므로 `KRX_ID`, `KRX_PW`가 비어 있으면 수집기는 시작 전에 실패한다. 이 값은 Git에 커밋하지 않는다.

## 실행 예시

KOSPI의 종목 기준정보와 일별 스냅샷을 처음 적재한다.

```powershell
python -m pipeline.fetch_market_data --date 20261113 --market KOSPI --sync-security-master
```

이후에는 종목 기준정보 동기화 없이 거래일마다 실행한다.

```powershell
python -m pipeline.fetch_market_data --date 20261113 --market KOSPI
```

`KOSDAQ`, `KONEX`도 같은 방식으로 별도 실행한다. 장 마감 확정 데이터 기준의 배치 작업이므로 충분히 늦은 저녁 시간에 실행한다.

## 수집 범위와 다음 단계

이 수집기는 가격과 외국인 보유량만 담당한다. 투자자별 매수·매도·순매수는 `pipeline/fetch_investor_trading.py`가 별도 적재한다.

```powershell
python -m pipeline.fetch_investor_trading --ticker 005930 --start 20260101 --end 20261113
```

이 수집기는 종목 하나와 기간 하나를 대상으로 모든 투자자 유형의 거래량·거래대금 매수, 매도, 순매수를 적재한다. 최초에는 KOSPI 200 같은 제한된 유니버스로 검증한 뒤 전체 시장으로 확장한다.
