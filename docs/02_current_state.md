# 현재 구현 현황

> 2026-11-20 저장소 코드 기준. 상세 구조·위험·작업별 완료 기준은 [프로젝트 분석과 실행 계획](06_project_assessment.md)에 있다. 실제 API 호출과 DB 적재 성공 여부는 확인하지 않았다.

## 현재 단계

목표는 외국인 투자자 수급과 한국 주식의 향후 수익률·위험의 관계를 검증하고, 근거가 있는 종목 신호와 위험 알림을 만드는 것이다. 현재는 **데이터 수집 기반과 탐색 노트북** 단계다.

| 영역 | 구현 파일 | 현재 범위 |
| --- | --- | --- |
| DB | `db/migrate.py`, `db/init_schema.sql`, `db/migrations/001_create_market_data_tables.sql` | PostgreSQL `raw` 스키마, ECOS 4개·시장 데이터 4개 테이블, 마이그레이션 이력 |
| 설정·연결 | `config/settings.py`, `db/connection.py`, `docker-compose.yml` | 환경변수 조회, DB 연결·트랜잭션, 로컬 DB 구성 |
| ECOS | `pipeline/fetch_data.py` | 직접 실행 시 환율·외환보유액 수집 및 UPSERT |
| KRX 가격·보유량 | `pipeline/fetch_market_data.py` | 지정일·시장 가격, 시총, 외국인 보유량 적재; 옵션으로 종목 마스터 갱신 |
| KRX 투자자 거래 | `pipeline/fetch_investor_trading.py` | 지정 종목·기간의 투자자별 매수·매도·순매수 수량/대금 적재 |
| 탐색 | `test/*.ipynb` | ECOS·DART 수집 실험, 삼성전자·거시지표 분석 |

ECOS 기준금리·국고채 수익률은 테이블과 모델만 있으며 직접 실행 경로에서 수집하지 않는다. CPI·M2·경기선행지수·뉴스심리지수·DART는 노트북 실험 단계다.

## 주요 공백

- `pipeline/runner.py`는 비어 있다. 전체 종목·거래일 반복, 재시도, 수집량·결측 검증이 없다.
- 종목 분류·상장 상태의 시점별 이력, 공개일 기준 데이터 결합, 분석 피처·신호·백테스트·화면이 없다.
- `test/`는 자동 테스트 모음이 아니다. 현재 환경에서 API·DB 통합 실행도 검증하지 못했다.
- 투자자 유형 매핑 충돌과 결측값 처리 등은 분석 전에 수정·검증해야 한다.
- 현재 노트북 소스는 ECOS 키를 환경변수에서 읽는다. 과거 Git 이력의 노출 여부는 별도 조사해야 한다.
