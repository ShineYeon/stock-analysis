"""Ingest daily investor buy, sell, and net flows for one KRX security."""

import argparse
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
from psycopg2.extras import execute_values
from pykrx import stock

from config.settings import get_required_setting
from db.connection import get_db_cursor


INVESTOR_TYPE_MAP = {
    "금융투자": "FINANCIAL_INVESTMENT",
    "보험": "INSURANCE",
    "투신": "INVESTMENT_TRUST",
    "사모": "PRIVATE_EQUITY",
    "은행": "BANK",
    "기타금융": "OTHER_FINANCIAL",
    "연기금": "PENSION",
    "기관합계": "INSTITUTION",
    "기타법인": "OTHER_CORPORATION",
    "개인": "INDIVIDUAL",
    "외국인": "FOREIGN",
    "외국인합계": "FOREIGN",
    "기타외국인": "OTHER_FOREIGN",
    "전체": "TOTAL",
}

TRADING_UPSERT = """
    INSERT INTO raw.investor_trading_daily (
        date, ticker, investor_type, investor_type_raw,
        buy_volume, sell_volume, net_volume,
        buy_value, sell_value, net_value,
        source, source_as_of_date
    ) VALUES %s
    ON CONFLICT (date, ticker, investor_type) DO UPDATE SET
        investor_type_raw = EXCLUDED.investor_type_raw,
        buy_volume = EXCLUDED.buy_volume,
        sell_volume = EXCLUDED.sell_volume,
        net_volume = EXCLUDED.net_volume,
        buy_value = EXCLUDED.buy_value,
        sell_value = EXCLUDED.sell_value,
        net_value = EXCLUDED.net_value,
        source = EXCLUDED.source,
        source_as_of_date = EXCLUDED.source_as_of_date,
        ingested_at = CURRENT_TIMESTAMP;
"""


def parse_date(value: str) -> str:
    """Validate and normalize a KRX date as YYYYMMDD."""
    try:
        return datetime.strptime(value, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYYMMDD format") from exc


def ensure_krx_credentials() -> None:
    get_required_setting("KRX_ID")
    get_required_setting("KRX_PW")


def _integer(value: Any) -> int:
    if value is None or pd.isna(value):
        return 0
    return int(value)


def fetch_trading_frames(
    ticker: str, start_date: str, end_date: str
) -> Dict[str, pd.DataFrame]:
    """Fetch detailed buy/sell/net frames for both value and volume."""
    ensure_krx_credentials()
    frames: Dict[str, pd.DataFrame] = {}
    for metric, loader in (
        ("value", stock.get_market_trading_value_by_date),
        ("volume", stock.get_market_trading_volume_by_date),
    ):
        for side in ("매수", "매도", "순매수"):
            frame = loader(start_date, end_date, ticker, on=side, detail=True)
            if frame.empty:
                raise RuntimeError(
                    f"No {metric} {side} data returned for {ticker} "
                    f"between {start_date} and {end_date}"
                )
            frames[f"{metric}_{side}"] = frame
    return frames


def build_investor_rows(
    ticker: str, frames: Dict[str, pd.DataFrame]
) -> List[Tuple[Any, ...]]:
    """Normalize pykrx detailed frames to the investor_trading_daily schema."""
    required = {
        "value_매수", "value_매도", "value_순매수",
        "volume_매수", "volume_매도", "volume_순매수",
    }
    missing = required.difference(frames)
    if missing:
        raise ValueError(f"Missing required trading frames: {sorted(missing)}")

    all_dates = sorted(set().union(*(frame.index for frame in frames.values())))
    all_investors = sorted(
        set().union(*(set(frame.columns) for frame in frames.values()))
    )
    rows: List[Tuple[Any, ...]] = []

    for trading_date in all_dates:
        date_value = pd.Timestamp(trading_date).date()
        for raw_type in all_investors:
            investor_type = INVESTOR_TYPE_MAP.get(raw_type, "OTHER")
            buy_volume = _frame_value(frames["volume_매수"], trading_date, raw_type)
            sell_volume = _frame_value(frames["volume_매도"], trading_date, raw_type)
            net_volume = _frame_value(frames["volume_순매수"], trading_date, raw_type)
            buy_value = _frame_value(frames["value_매수"], trading_date, raw_type)
            sell_value = _frame_value(frames["value_매도"], trading_date, raw_type)
            net_value = _frame_value(frames["value_순매수"], trading_date, raw_type)

            if all(value == 0 for value in (
                buy_volume, sell_volume, net_volume,
                buy_value, sell_value, net_value,
            )):
                continue

            rows.append((
                date_value, ticker.zfill(6), investor_type, raw_type,
                buy_volume, sell_volume, net_volume,
                buy_value, sell_value, net_value,
                "KRX", date_value,
            ))
    return rows


def _frame_value(frame: pd.DataFrame, date: Any, investor: str) -> int:
    if date not in frame.index or investor not in frame.columns:
        return 0
    value = frame.loc[date, investor]
    if isinstance(value, pd.Series):
        raise ValueError(f"Duplicate trading value for {date} / {investor}")
    return _integer(value)


def upsert_investor_trading(ticker: str, start_date: str, end_date: str) -> int:
    frames = fetch_trading_frames(ticker, start_date, end_date)
    rows = build_investor_rows(ticker, frames)
    if not rows:
        raise RuntimeError("No investor trading rows were generated")

    with get_db_cursor() as (cursor, _):
        execute_values(cursor, TRADING_UPSERT, rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest KRX investor trading data for one security."
    )
    parser.add_argument("--ticker", required=True, help="six-digit KRX ticker")
    parser.add_argument("--start", required=True, type=parse_date, help="YYYYMMDD")
    parser.add_argument("--end", required=True, type=parse_date, help="YYYYMMDD")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error("--start must not be after --end")

    row_count = upsert_investor_trading(args.ticker, args.start, args.end)
    print(f"{args.ticker.zfill(6)}: {row_count} investor trading rows upserted")


if __name__ == "__main__":
    main()
