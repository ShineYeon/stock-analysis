-- Core market-data tables for foreign-investor flow analysis.
-- Run this after db/init_schema.sql.

CREATE TABLE IF NOT EXISTS raw.security_master (
    ticker VARCHAR(20) PRIMARY KEY,
    isin VARCHAR(20),
    name VARCHAR(200) NOT NULL,
    market VARCHAR(20) NOT NULL,
    sector VARCHAR(200),
    industry VARCHAR(200),
    listing_date DATE,
    delisting_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    source VARCHAR(50) NOT NULL DEFAULT 'KRX',
    source_as_of_date DATE,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw.stock_prices_daily (
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    open_price NUMERIC(18, 4),
    high_price NUMERIC(18, 4),
    low_price NUMERIC(18, 4),
    close_price NUMERIC(18, 4) NOT NULL,
    volume BIGINT,
    trading_value BIGINT,
    market_cap BIGINT,
    listed_shares BIGINT,
    change_rate NUMERIC(10, 6),
    source VARCHAR(50) NOT NULL DEFAULT 'KRX',
    source_as_of_date DATE,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT stock_prices_daily_pkey PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS stock_prices_daily_ticker_date_idx
    ON raw.stock_prices_daily (ticker, date DESC);

CREATE TABLE IF NOT EXISTS raw.investor_trading_daily (
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    investor_type VARCHAR(30) NOT NULL,
    investor_type_raw VARCHAR(50) NOT NULL,
    buy_volume BIGINT NOT NULL DEFAULT 0,
    sell_volume BIGINT NOT NULL DEFAULT 0,
    net_volume BIGINT NOT NULL DEFAULT 0,
    buy_value BIGINT NOT NULL DEFAULT 0,
    sell_value BIGINT NOT NULL DEFAULT 0,
    net_value BIGINT NOT NULL DEFAULT 0,
    source VARCHAR(50) NOT NULL DEFAULT 'KRX',
    source_as_of_date DATE,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT investor_trading_daily_pkey PRIMARY KEY (date, ticker, investor_type)
);

CREATE INDEX IF NOT EXISTS investor_trading_daily_ticker_date_idx
    ON raw.investor_trading_daily (ticker, date DESC);

CREATE INDEX IF NOT EXISTS investor_trading_daily_foreign_date_idx
    ON raw.investor_trading_daily (date, ticker)
    WHERE investor_type = 'FOREIGN';

CREATE TABLE IF NOT EXISTS raw.foreign_ownership_daily (
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    listed_shares BIGINT,
    foreign_shares BIGINT NOT NULL,
    foreign_ownership_pct NUMERIC(9, 6) NOT NULL,
    foreign_limit_shares BIGINT,
    foreign_limit_exhaustion_pct NUMERIC(9, 6),
    source VARCHAR(50) NOT NULL DEFAULT 'KRX',
    source_as_of_date DATE,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT foreign_ownership_daily_pkey PRIMARY KEY (date, ticker),
    CONSTRAINT foreign_ownership_pct_range CHECK (
        foreign_ownership_pct >= 0 AND foreign_ownership_pct <= 100
    ),
    CONSTRAINT foreign_limit_exhaustion_pct_range CHECK (
        foreign_limit_exhaustion_pct IS NULL
        OR (foreign_limit_exhaustion_pct >= 0 AND foreign_limit_exhaustion_pct <= 100)
    )
);

CREATE INDEX IF NOT EXISTS foreign_ownership_daily_ticker_date_idx
    ON raw.foreign_ownership_daily (ticker, date DESC);

COMMENT ON TABLE raw.security_master IS 'KRX listed-security reference data';
COMMENT ON TABLE raw.stock_prices_daily IS 'Daily price, turnover, and market-cap data by security';
COMMENT ON TABLE raw.investor_trading_daily IS 'Daily buy, sell, and net flow by security and investor type';
COMMENT ON TABLE raw.foreign_ownership_daily IS 'Daily foreign ownership and limit data by security';
