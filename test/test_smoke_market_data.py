"""Checks for the limited-universe ingestion verification path."""

import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from pipeline.fetch_market_data import merge_market_cap, select_snapshot_tickers
from pipeline.smoke_market_data import run_sample, validate_sample


def stored_sample(close=70000):
    day = date(2026, 11, 13)
    return {
        "raw.stock_prices_daily": (
            (day, "005930", 69000, 71000, 68000, close, 100, 7000000,
             100000000, 1000000, 1, "KRX", day),
        ),
        "raw.foreign_ownership_daily": (
            (day, "005930", 1000000, 500000, 50, 1000000, 50, "KRX", day),
        ),
        "raw.investor_trading_daily": (
            (day, "005930", "FOREIGN", "외국인", 10, 5, 5,
             700000, 350000, 350000, "KRX", day),
        ),
    }


class SampleIngestionTest(unittest.TestCase):
    def test_market_cap_response_replaces_duplicate_price_column(self):
        prices = pd.DataFrame(
            {"종가": [70000], "시가총액": [1]}, index=["005930"]
        )
        market_cap = pd.DataFrame(
            {"시가총액": [70000000], "상장주식수": [1000]},
            index=["005930"],
        )
        merged = merge_market_cap(prices, market_cap)
        self.assertEqual(merged.loc["005930", "시가총액"], 70000000)
        self.assertEqual(merged.columns.tolist().count("시가총액"), 1)

    def test_ticker_selection_requires_price_and_ownership(self):
        prices = pd.DataFrame(
            {"종가": [70000, 30000]}, index=["005930", "000660"]
        )
        ownership = pd.DataFrame(
            {"보유수량": [500000], "지분율": [50]},
            index=["005930"],
        )
        with self.assertRaisesRegex(ValueError, "Missing KRX snapshot rows"):
            select_snapshot_tickers(prices, ownership, ("005930", "000660"))

        selected_prices, selected_ownership = select_snapshot_tickers(
            prices, ownership, ("005930",)
        )
        self.assertEqual(selected_prices.index.tolist(), ["005930"])
        self.assertEqual(selected_ownership.index.tolist(), ["005930"])

    def test_sample_requires_foreign_flow(self):
        sample = stored_sample()
        sample["raw.investor_trading_daily"] = (
            (*sample["raw.investor_trading_daily"][0][:2], "INDIVIDUAL",
             *sample["raw.investor_trading_daily"][0][3:]),
        )
        with self.assertRaisesRegex(RuntimeError, "expected one FOREIGN"):
            validate_sample(sample, ["20261113"], ["005930"])

    def test_sample_rejects_inconsistent_net_flow(self):
        sample = stored_sample()
        row = list(sample["raw.investor_trading_daily"][0])
        row[9] = 1
        sample["raw.investor_trading_daily"] = (tuple(row),)
        with self.assertRaisesRegex(RuntimeError, "buy minus sell"):
            validate_sample(sample, ["20261113"], ["005930"])

    @patch("pipeline.smoke_market_data.read_sample")
    @patch("pipeline.smoke_market_data.upsert_investor_trading")
    @patch("pipeline.smoke_market_data.upsert_snapshot", return_value=(1, 1))
    def test_second_pass_checks_persisted_values(
        self, snapshot, trading, read_sample
    ):
        read_sample.side_effect = [stored_sample(), stored_sample(close=71000)]
        with self.assertRaisesRegex(RuntimeError, "changed on the second"):
            run_sample(["20261113"], ["005930"], "KOSPI")
        self.assertEqual(snapshot.call_count, 2)
        self.assertEqual(trading.call_count, 2)

    @patch("pipeline.smoke_market_data.read_sample", side_effect=lambda *_: stored_sample())
    @patch("pipeline.smoke_market_data.upsert_investor_trading")
    @patch("pipeline.smoke_market_data.upsert_snapshot", return_value=(1, 1))
    def test_identical_second_pass_succeeds(self, snapshot, trading, read_sample):
        counts = run_sample(["20261113"], ["005930"], "KOSPI")
        self.assertEqual(counts["raw.stock_prices_daily"], 1)
        self.assertEqual(counts["raw.foreign_ownership_daily"], 1)
        self.assertEqual(counts["raw.investor_trading_daily"], 1)
        self.assertEqual(snapshot.call_count, 2)
        self.assertEqual(trading.call_count, 2)


if __name__ == "__main__":
    unittest.main()
