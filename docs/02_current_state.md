# 현재 구현 현황

## 현재 프로젝트의 역할

현재 코드는 완성된 추천 시스템이 아니라, 한국은행 ECOS 거시지표를 PostgreSQL에 적재하고 삼성전자 사례의 상관관계를 탐색하는 **데이터 수집·분석 기반 단계**다.

## 정식 코드에 구현된 것

| 영역 | 파일 | 현황 |
| --- | --- | --- |
| 환경변수 예시 | `.env.example` | PostgreSQL, ECOS, KRX, DART 키 이름 정의 |
| DB 연결 유틸리티 | `db/connection.py` | 접속, 트랜잭션, 롤백 context manager 구현 |
| 데이터 모델 | `db/models.py` | 4개 ECOS 테이블 dataclass와 행 파서 구현 |
| 스키마 | `db/init_schema.sql` | `raw` 스키마와 4개 테이블 생성 |
| ECOS 수집 | `pipeline/fetch_data.py` | 월별 요청 분할, API 호출, UPSERT 구현 |

`pipeline/fetch_data.py`를 직접 실행하면 현재 아래 두 데이터만 수집한다.

| 테이블 | ECOS 통계표 | 주기 | 시작 시점 |
| --- | --- | --- | --- |
| `raw.krw_exchange_rates` | `731Y001` | 일별 | 1964-05-04 |
| `raw.fx_reserves` | `732Y001` | 월별 | 1971-01 |

스키마와 모델에는 아래 테이블도 준비되어 있으나, 정식 실행 경로에서는 아직 수집하지 않는다.

| 테이블 | 내용 |
| --- | --- |
| `raw.bok_base_rates` | 한국은행 기준금리 등 |
| `raw.ktb_yields` | 국고채 및 시장금리 |

## 노트북에서 탐색·검증한 것

`test/test_fetch_data.ipynb`에는 정식 코드로 옮겨지지 않은 수집 실험이 있다.

- 경기종합지수 선행지수
- 소비자물가지수(CPI)
- 광의통화(M2)
- 뉴스심리지수
- DART 상장법인 주요 재무계정
- ECOS 통계표·항목 조회 및 API 동작 확인

`test/Analysis.ipynb`에는 다음 탐색 분석이 있다.

- FinanceDataReader와 PyKRX로 삼성전자(`005930`) 가격·거래량 조회 및 시각화
- 원/달러 환율, 외환보유액, 국고채 3년물, CPI, M2를 월말 기준으로 병합
- 삼성전자 가격과 거시지표의 수준·월간변화율 상관관계 히트맵 및 정규화 추이 시각화

## 아직 구현되지 않은 핵심 범위

- 외국인 순매수, 보유비중, 투자자별 거래대금 같은 **외국인 수급 데이터**
- 전 종목 OHLCV, 거래대금, 시가총액, 업종 분류, 상장/상장폐지 이력
- 종목별 재무·밸류에이션·공시 이벤트의 정식 적재
- 외국인 심리 지수, 추천 점수, 위험 알림 규칙 또는 예측 모델
- 백테스트, 성과 추적, 알림 전달, 대시보드/API

## 구조상 정리할 부분

- `config/settings.py`, `pipeline/runner.py`, `requirements.txt`가 비어 있다.
- `fetch_data.py`가 `db/connection.py`, `db/models.py`의 공통 로직을 사용하지 않아 DB 설정·파싱 코드가 중복된다.
- 분석 노트북이 조회하는 CPI·M2 테이블은 `db/init_schema.sql`에 정의되어 있지 않다. 새 환경에서 재현 가능한 마이그레이션이 필요하다.
- 현재 `test/`는 자동 테스트가 아니라 탐색 노트북 저장소다.
- 노트북에 ECOS 키가 하드코딩되어 Git 이력에 포함되어 있다. 키 폐기·재발급 후 제거가 필요하다.

