# DB 마이그레이션

새 데이터베이스에는 먼저 `db/init_schema.sql`을 실행한 다음, 번호 순서대로 이 디렉터리의 SQL 파일을 실행한다.

```powershell
psql -d stock_analysis -f db/init_schema.sql
psql -d stock_analysis -f db/migrations/001_create_market_data_tables.sql
```

이미 생성된 데이터베이스에는 아직 적용하지 않은 마이그레이션 파일만 실행한다. 각 파일은 `IF NOT EXISTS`를 사용하므로 같은 파일을 다시 실행해도 기존 테이블과 인덱스는 유지된다.
