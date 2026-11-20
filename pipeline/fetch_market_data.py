"""Ingest KRX end-of-day prices and foreign ownership data into PostgreSQL."""

import argparse
import io
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Iterable, List, Optional, Tuple

import pandas as pd
from psycopg2.extras import execute_values

from config.settings import get_required_setting
from db.connection import get_db_cursor


PRICE_UPSERT = """
    INSERT INTO raw.stock_prices_daily (
        date, ticker, open_price, high_price, low_price, close_price,
        volume, trading_value, market_cap, listed_shares, change_rate,
        source, source_as_of_date
    ) VALUES %s
    ON CONFLICT (date, ticker) DO UPDATE SET
        open_price = EXCLUDED.open_price,
        high_price = EXCLUDED.high_price,
        low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price,
        volume = EXCLUDED.volume,
        trading_value = EXCLUDED.trading_value,
        market_cap = EXCLUDED.market_cap,
        listed_shares = EXCLUDED.listed_shares,
        change_rate = EXCLUDED.change_rate,
        source = EXCLUDED.source,
        source_as_of_date = EXCLUDED.source_as_of_date,
        ingested_at = CURRENT_TIMESTAMP;
"""

OWNERSHIP_UPSERT = """
    INSERT INTO raw.foreign_ownership_daily (
        date, ticker, listed_shares, foreign_shares, foreign_ownership_pct,
        foreign_limit_shares, foreign_limit_exhaustion_pct, source,
        source_as_of_date
    ) VALUES %s
    ON CONFLICT (date, ticker) DO UPDATE SET
        listed_shares = EXCLUDED.listed_shares,
        foreign_shares = EXCLUDED.foreign_shares,
        foreign_ownership_pct = EXCLUDED.foreign_ownership_pct,
        foreign_limit_shares = EXCLUDED.foreign_limit_shares,
        foreign_limit_exhaustion_pct = EXCLUDED.foreign_limit_exhaustion_pct,
        source = EXCLUDED.source,
        source_as_of_date = EXCLUDED.source_as_of_date,
        ingested_at = CURRENT_TIMESTAMP;
"""

SECURITY_UPSERT = """
    INSERT INTO raw.security_master (
        ticker, name, market, is_active, source, source_as_of_date
    ) VALUES %s
    ON CONFLICT (ticker) DO UPDATE SET
        name = EXCLUDED.name,
        market = EXCLUDED.market,
        is_active = EXCLUDED.is_active,
        source = EXCLUDED.source,
        source_as_of_date = EXCLUDED.source_as_of_date,
        ingested_at = CURRENT_TIMESTAMP;
"""


def parse_date(value: str) -> datetime:
    """Parse a KRX query date in YYYYMMDD format."""
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYYMMDD format") from exc


def _number(value: Any, integer: bool = False) -> Optional[Any]:
    if value is None or pd.isna(value):
        return None
    return int(value) if integer else float(value)


def ensure_krx_credentials() -> None:
    """Fail early because KRX-backed pykrx requests require a login session."""
    get_required_setting("KRX_ID")
    get_required_setting("KRX_PW")


def merge_market_cap(prices: pd.DataFrame, market_cap: pd.DataFrame) -> pd.DataFrame:
    """Use the dedicated market-cap response when both frames contain cap fields."""
    columns = ["시가총액", "상장주식수"]
    if not market_cap.index.is_unique:
        raise ValueError("Duplicate ticker in KRX market-cap snapshot")
    missing = set(columns).difference(market_cap.columns)
    if missing:
        raise ValueError(f"Missing KRX market-cap columns: {sorted(missing)}")
    return prices.drop(columns=columns, errors="ignore").join(
        market_cap[columns], how="left"
    )


def fetch_snapshot_frames(as_of_date: str, market: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch one market's final daily price and foreign-ownership snapshots."""
    ensure_krx_credentials()
    # pykrx prints the account ID during login. Keep it out of command output.
    with redirect_stdout(io.StringIO()):
        from pykrx import stock
        prices = stock.get_market_ohlcv_by_ticker(as_of_date, market=market)
        market_cap = stock.get_market_cap_by_ticker(as_of_date, market=market)
        ownership = stock.get_exhaustion_rates_of_foreign_investment(
            as_of_date, market=market
        )

    if prices.empty:
        raise RuntimeError(f"No KRX price data returned for {market} on {as_of_date}")
    if ownership.empty:
        raise RuntimeError(f"No KRX foreign-ownership data returned for {market} on {as_of_date}")

    prices = merge_market_cap(prices, market_cap)
    return prices, ownership


def build_price_rows(as_of_date: str, prices: pd.DataFrame) -> List[Tuple[Any, ...]]:
    rows: List[Tuple[Any, ...]] = []
    for ticker, row in prices.iterrows():
        rows.append((
            as_of_date, str(ticker).zfill(6), _number(row.get("시가")),
            _number(row.get("고가")), _number(row.get("저가")),
            _number(row.get("종가")), _number(row.get("거래량"), integer=True),
            _number(row.get("거래대금"), integer=True),
            _number(row.get("시가총액"), integer=True),
            _number(row.get("상장주식수"), integer=True), _number(row.get("등락률")),
            "KRX", as_of_date,
        ))
    return rows


def build_ownership_rows(as_of_date: str, ownership: pd.DataFrame) -> List[Tuple[Any, ...]]:
    rows: List[Tuple[Any, ...]] = []
    for ticker, row in ownership.iterrows():
        foreign_shares = _number(row.get("보유수량"), integer=True)
        foreign_pct = _number(row.get("지분율"))
        if foreign_shares is None or foreign_pct is None:
            continue
        rows.append((
            as_of_date, str(ticker).zfill(6),
            _number(row.get("상장주식수"), integer=True), foreign_shares, foreign_pct,
            _number(row.get("한도수량"), integer=True), _number(row.get("한도소진율")),
            "KRX", as_of_date,
        ))
    return rows


def select_snapshot_tickers(
    prices: pd.DataFrame, ownership: pd.DataFrame, tickers: Iterable[str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Require every requested ticker in both KRX snapshots before writing."""
    requested = tuple(tickers)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("Specify one or more unique tickers")
    if not prices.index.is_unique or not ownership.index.is_unique:
        raise ValueError("Duplicate ticker in a KRX snapshot")
    missing_prices = set(requested).difference(prices.index)
    missing_ownership = set(requested).difference(ownership.index)
    if missing_prices or missing_ownership:
        raise ValueError(
            f"Missing KRX snapshot rows: prices={sorted(missing_prices)}, "
            f"ownership={sorted(missing_ownership)}"
        )
    selected_prices = prices.loc[list(requested)]
    selected_ownership = ownership.loc[list(requested)]
    if selected_prices["종가"].isna().any():
        raise ValueError("Missing close price in selected KRX snapshot")
    if selected_ownership[["보유수량", "지분율"]].isna().any().any():
        raise ValueError("Missing foreign ownership in selected KRX snapshot")
    return selected_prices, selected_ownership


def upsert_snapshot(
    as_of_date: str, market: str, tickers: Optional[Iterable[str]] = None
) -> Tuple[int, int]:
    """Fetch and atomically upsert one KRX market snapshot."""
    prices, ownership = fetch_snapshot_frames(as_of_date, market)
    if tickers is not None:
        prices, ownership = select_snapshot_tickers(prices, ownership, tickers)
    price_rows = build_price_rows(as_of_date, prices)
    ownership_rows = build_ownership_rows(as_of_date, ownership)
    if not ownership_rows:
        raise RuntimeError(f"No valid foreign-ownership rows for {market} on {as_of_date}")

    with get_db_cursor() as (cursor, _):
        execute_values(cursor, PRICE_UPSERT, price_rows)
        execute_values(cursor, OWNERSHIP_UPSERT, ownership_rows)
    return len(price_rows), len(ownership_rows)


def sync_security_master(as_of_date: str, markets: Iterable[str]) -> int:
    """Refresh ticker/name/market data. Run occasionally, not every day."""
    ensure_krx_credentials()
    rows: List[Tuple[Any, ...]] = []
    with redirect_stdout(io.StringIO()):
        from pykrx import stock
        for market in markets:
            for ticker in stock.get_market_ticker_list(as_of_date, market=market):
                rows.append((
                    ticker, stock.get_market_ticker_name(ticker), market,
                    True, "KRX", as_of_date,
                ))
    if not rows:
        raise RuntimeError(f"No KRX tickers returned for {as_of_date}")

    with get_db_cursor() as (cursor, _):
        execute_values(cursor, SECURITY_UPSERT, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest KRX daily price and foreign-ownership snapshots."
    )
    parser.add_argument(
        "--date", type=parse_date, default=datetime.today(),
        help="KRX trading date in YYYYMMDD (default: today)",
    )
    parser.add_argument(
        "--market", choices=("KOSPI", "KOSDAQ", "KONEX"), default="KOSPI",
        help="market to collect (default: KOSPI)",
    )
    parser.add_argument(
        "--sync-security-master", action="store_true",
        help="also refresh ticker/name/market reference data",
    )
    args = parser.parse_args()
    as_of_date = args.date.strftime("%Y%m%d")

    if args.sync_security_master:
        count = sync_security_master(as_of_date, (args.market,))
        print(f"security_master: {count} rows upserted")

    prices, ownership = upsert_snapshot(as_of_date, args.market)
    print(f"{args.market} {as_of_date}: {prices} price rows, {ownership} ownership rows upserted")


if __name__ == "__main__":
    main()
