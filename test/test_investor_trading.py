"""Focused validation of investor trading rows before database insertion."""

import unittest

import pandas as pd

from pipeline.fetch_investor_trading import FRAME_KEYS, build_investor_rows


def sample_frames(columns=("외국인", "외국인합계", "기타외국인")):
    dates = pd.to_datetime(["2026-11-13"])
    return {
        key: pd.DataFrame([[0] * len(columns)], index=dates, columns=columns)
        for key in FRAME_KEYS
    }


class InvestorTradingRowsTest(unittest.TestCase):
    def test_foreign_detail_and_total_have_distinct_keys(self):
        rows = build_investor_rows("5930", sample_frames())
        by_raw_type = {row[3]: row for row in rows}

        self.assertEqual(by_raw_type["외국인"][2], "FOREIGN")
        self.assertEqual(by_raw_type["외국인합계"][2], "FOREIGN_TOTAL")
        self.assertEqual(by_raw_type["기타외국인"][2], "OTHER_FOREIGN")
        self.assertEqual(len({row[:3] for row in rows}), len(rows))
        self.assertEqual(by_raw_type["외국인"][1], "005930")
        self.assertTrue(all(row[4:10] == (0,) * 6 for row in rows))

    def test_missing_value_is_rejected_instead_of_becoming_zero(self):
        frames = sample_frames(("외국인",))
        frames["value_매수"].iloc[0, 0] = None
        with self.assertRaisesRegex(ValueError, "Missing investor trading value"):
            build_investor_rows("005930", frames)

    def test_mismatched_columns_are_rejected(self):
        frames = sample_frames(("외국인",))
        frames["volume_매도"] = frames["volume_매도"].rename(
            columns={"외국인": "개인"}
        )
        with self.assertRaisesRegex(ValueError, "Mismatched dates or investor types"):
            build_investor_rows("005930", frames)

    def test_unknown_type_is_rejected_instead_of_collapsing_to_other(self):
        with self.assertRaisesRegex(ValueError, "Unknown investor types"):
            build_investor_rows("005930", sample_frames(("새유형",)))


if __name__ == "__main__":
    unittest.main()
