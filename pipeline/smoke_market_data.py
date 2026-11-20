"""Backfill a tiny KRX sample twice and verify its persisted rows."""

import argparse
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Tuple

from db.connection import get_db_cursor
from pipeline.fetch_investor_trading import upsert_investor_trading
from pipeline.fetch_market_data import upsert_snapshot


TABLE_COLUMNS = {
    "raw.stock_prices_daily": (
        "date", "ticker", "open_price", "high_price", "low_price",
        "close_price", "volume", "trading_value", "market_cap",
        "listed_shares", "change_rate", "source", "source_as_of_date",
    ),
    "raw.foreign_ownership_daily": (
        "date", "ticker", "listed_shares", "foreign_shares",
        "foreign_ownership_pct", "foreign_limit_shares",
        "foreign_limit_exhaustion_pct", "source", "source_as_of_date",
    ),
    "raw.investor_trading_daily": (
        "date", "ticker", "investor_type", "investor_type_raw",
        "buy_volume", "sell_volume", "net_volume", "buy_value",
        "sell_value", "net_value", "source", "source_as_of_date",
    ),
}


def validate_inputs(dates: list[str], tickers: list[str]) -> None:
    if not dates or len(dates) != len(set(dates)):
        raise ValueError("Specify one or more unique dates")
    for date in dates:
        datetime.strptime(date, "%Y%m%d")
    if not tickers or len(tickers) != len(set(tickers)):
        raise ValueError("Specify one or more unique tickers")
    if any(not re.fullmatch(r"[0-9]{6}", ticker) for ticker in tickers):
        raise ValueError("Tickers must contain exactly six digits")


def read_sample(dates: list[str], tickers: list[str]) -> Dict[str, Tuple[tuple, ...]]:
    """Read stable stored values, excluding the expected-to-change ingested_at."""
    result = {}
    query_dates = [datetime.strptime(day, "%Y%m%d").date().isoformat() for day in dates]
    with get_db_cursor() as (cursor, _):
        for table, columns in TABLE_COLUMNS.items():
            # Both identifiers come only from the fixed TABLE_COLUMNS constant.
            cursor.execute(
                f"SELECT {', '.join(columns)} FROM {table} "
                "WHERE date = ANY(%s::date[]) AND ticker = ANY(%s::text[]) "
                f"ORDER BY date, ticker, {columns[2]}",
                (query_dates, tickers),
            )
            result[table] = tuple(cursor.fetchall())
    return result


def validate_sample(
    sample: Dict[str, Tuple[tuple, ...]], dates: list[str], tickers: list[str]
) -> Dict[str, int]:
    expected = {(datetime.strptime(day, "%Y%m%d").date(), ticker)
                for day in dates for ticker in tickers}
    counts = {}
    for table, rows in sample.items():
        by_pair = defaultdict(list)
        for row in rows:
            by_pair[row[:2]].append(row)
        if set(by_pair) != expected:
            raise RuntimeError(f"{table}: missing sample rows for {sorted(expected - set(by_pair))}")
        if table != "raw.investor_trading_daily":
            if any(len(group) != 1 for group in by_pair.values()):
                raise RuntimeError(f"{table}: expected one row per date and ticker")
        else:
            if any(
                sum(row[2] == "FOREIGN" for row in group) != 1
                for group in by_pair.values()
            ):
                raise RuntimeError("investor trading: expected one FOREIGN row per date and ticker")
        counts[table] = len(rows)

    prices = sample["raw.stock_prices_daily"]
    if any(any(value is None for value in row[2:10]) for row in prices):
        raise RuntimeError("price snapshot: missing OHLCV, trading value, or market cap")
    ownership = sample["raw.foreign_ownership_daily"]
    if any(row[3] is None or row[4] is None for row in ownership):
        raise RuntimeError("foreign ownership snapshot: missing shares or percentage")
    trading = sample["raw.investor_trading_daily"]
    if any(
        row[4] - row[5] != row[6] or row[7] - row[8] != row[9]
        for row in trading
    ):
        raise RuntimeError("investor trading: buy minus sell does not equal net")
    return counts


def run_sample(dates: list[str], tickers: list[str], market: str) -> Dict[str, int]:
    """Ingest one small sample twice and compare persistent data after each pass."""
    validate_inputs(dates, tickers)
    first_sample = None
    for pass_number in (1, 2):
        for day in dates:
            price_count, ownership_count = upsert_snapshot(day, market, tickers)
            if (price_count, ownership_count) != (len(tickers), len(tickers)):
                raise RuntimeError(f"{day}: incomplete price or ownership snapshot")
            for ticker in tickers:
                upsert_investor_trading(ticker, day, day)
        sample = read_sample(dates, tickers)
        counts = validate_sample(sample, dates, tickers)
        if first_sample is not None and sample != first_sample:
            raise RuntimeError("Stored sample changed on the second ingestion pass")
        first_sample = sample
        print(f"pass {pass_number}: {counts}")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and verify a small KRX date/ticker sample twice."
    )
    parser.add_argument("--dates", nargs="+", required=True, help="YYYYMMDD dates")
    parser.add_argument("--tickers", nargs="+", required=True, help="six-digit tickers")
    parser.add_argument("--market", choices=("KOSPI", "KOSDAQ", "KONEX"), required=True)
    args = parser.parse_args()
    run_sample(args.dates, args.tickers, args.market)


if __name__ == "__main__":
    main()
