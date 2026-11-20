"""R1: KRX execution plans are validated before any external I/O."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

from pipeline.krx.plan import build_plan
from pipeline.krx.runner import main


class RunnerPlanTest(unittest.TestCase):
    def test_plan_has_calendar_candidates_without_claiming_trading_days(self):
        plan = build_plan(
            "KOSPI", date(2026, 11, 13), date(2026, 11, 15),
            ["005930", "000660"],
        )
        self.assertEqual(plan.calendar_days, 3)
        self.assertEqual(len(list(plan.candidate_dates())), 3)
        output = io.StringIO()
        with redirect_stdout(output):
            main([
                "--market", "KOSPI", "--start", "20261113",
                "--end", "20261115", "--tickers", "005930", "000660",
                "--dry-run",
            ])
        self.assertIn("trading days not checked", output.getvalue())
        self.assertIn("No API requests or database writes", output.getvalue())

    def test_invalid_scope_is_rejected(self):
        start, end = date(2026, 11, 13), date(2026, 11, 12)
        with self.assertRaisesRegex(ValueError, "start date"):
            build_plan("KOSPI", start, end, ["005930"])
        with self.assertRaisesRegex(ValueError, "duplicate tickers"):
            build_plan("KOSPI", end, start, ["005930", "005930"])
        with self.assertRaisesRegex(ValueError, "six digits"):
            build_plan("KOSPI", end, start, ["5930"])
        with self.assertRaisesRegex(ValueError, "market"):
            build_plan("INVALID", end, start, ["005930"])

    def test_cli_requires_dry_run_and_strict_date_format(self):
        for extra in ([], ["--dry-run", "--start", "2026-11-13"]):
            args = [
                "--market", "KOSPI", "--start", "20261113",
                "--end", "20261113", "--tickers", "005930",
                *extra,
            ]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)


if __name__ == "__main__":
    unittest.main()
