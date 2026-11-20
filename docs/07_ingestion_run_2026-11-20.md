# 2026-11-20 로컬 데이터 적재 기록

로컬 Docker PostgreSQL 16의 `stock_analysis` 데이터베이스에 `db.migrate`를 적용한 뒤 실제 KRX·ECOS 응답을 적재했다. 비밀값은 Git에서 제외된 `.env`에만 두고 이 기록에는 남기지 않는다. 데이터는 저장소 파일이 아니라 Docker 볼륨 `plankton_postgres_data`에 있다.

## 적재 범위와 확인 결과

| 테이블 | 행 수 | 날짜 범위 | 확인 |
| --- | ---: | --- | --- |
| `raw.krw_exchange_rates` | 11,094 | 2025-11-03 ~ 2026-11-19, 258일 | 43개 통화 항목 |
| `raw.fx_reserves` | 60 | 2025-11-01 ~ 2026-10-01, 12개월 | 월별 5개 항목 |
| `raw.stock_prices_daily` | 10 | 2026-11-13 ~ 2026-11-19, 5거래일 | `005930`, `000660` 각 5행 |
| `raw.foreign_ownership_daily` | 10 | 같은 5거래일 | 각 날짜·종목 1행 |
| `raw.investor_trading_daily` | 120 | 같은 5거래일 | 각 날짜·종목 12개 투자자 유형 |

시장 표본은 `pipeline.smoke_market_data`로 두 번 적재해 `ingested_at`을 제외한 저장값이 같은지 비교했다. 순매수 수량/대금 계산 불일치, 주요 가격 필드 결측, 외국인 보유량·지분율 결측은 각각 0건이었다. 첫 실행에서 pykrx 가격 응답에 시가총액이 이미 포함돼 있음을 발견해 중복 열 결합을 수정한 후 다시 실행했다.

## 재현 명령

```bash
docker compose up -d postgres
python -m db.migrate
python -m pipeline.smoke_market_data --market KOSPI --dates 20261113 20261116 20261117 20261118 20261119 --tickers 005930 000660
```

ECOS는 `pipeline.fetch_data.fetch_and_upsert`를 사용해 환율 일별 `2025-11-01`~`2026-11-19`, 외환보유액 월별 같은 기간을 요청했다. `fetch_data.py`를 직접 실행하면 1960~1970년대부터 전체 구간을 요청하므로 이번 표본과 범위가 다르다.

이 결과는 **로컬 표본 적재**다. KOSPI 전체 종목과 장기간 시장 이력, 종목 마스터, 기준금리·국고채 등은 아직 적재하지 않았다. KRX 인증은 재접속 시 한 차례 실패 후 다시 성공했으므로, 전체 백필 전 로그인 재시도와 실패 기록을 보강해야 한다.
