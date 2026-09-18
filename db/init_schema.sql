-- 1. raw 스키마 생성
CREATE SCHEMA IF NOT EXISTS raw;

-- 2. 환율 테이블 (일별)
CREATE TABLE IF NOT EXISTS raw.krw_exchange_rates (
    date DATE NOT NULL,
    stat_code VARCHAR(20) NOT NULL,
    stat_name VARCHAR(100),
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(100),
    cycle VARCHAR(10) NOT NULL,
    unit_name VARCHAR(50),
    exchange_rate NUMERIC(10, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT krw_exchange_rates_pkey PRIMARY KEY (date, stat_code, item_code)
);
COMMENT ON TABLE raw.krw_exchange_rates IS '주요국 통화의 대원화 환율 raw 데이터 (ECOS)';

-- 3. 외환보유액 테이블 (월별)
CREATE TABLE IF NOT EXISTS raw.fx_reserves (
    date DATE NOT NULL,
    stat_code VARCHAR(20) NOT NULL,
    stat_name VARCHAR(100),
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(100),
    cycle VARCHAR(10) NOT NULL,
    unit_name VARCHAR(50),
    amount BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fx_reserves_pkey PRIMARY KEY (date, stat_code, item_code)
);
COMMENT ON TABLE raw.fx_reserves IS '월별 외환보유액 raw 데이터 (ECOS)';

-- 4. 한국은행 기준금리 테이블 (일별)
CREATE TABLE IF NOT EXISTS raw.bok_base_rates (
    date DATE NOT NULL,
    stat_code VARCHAR(20) NOT NULL,
    stat_name VARCHAR(100),
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(100),
    cycle VARCHAR(10) NOT NULL,
    unit_name VARCHAR(50),
    base_rate NUMERIC(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bok_base_rates_pkey PRIMARY KEY (date, stat_code, item_code)
);
COMMENT ON TABLE raw.bok_base_rates IS '한국은행 기준금리 raw 데이터 (ECOS)';

-- 5. 국고채 수익률 및 시장금리 테이블 (일별)
CREATE TABLE IF NOT EXISTS raw.ktb_yields (
    date DATE NOT NULL,
    stat_code VARCHAR(20) NOT NULL,
    stat_name VARCHAR(100),
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(100),
    cycle VARCHAR(10) NOT NULL,
    unit_name VARCHAR(50),
    yield_rate NUMERIC(6, 3) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ktb_yields_pkey PRIMARY KEY (date, stat_code, item_code)
);
COMMENT ON TABLE raw.ktb_yields IS '국고채 수익률 및 시장금리 raw 데이터 (ECOS)';