"""Pure KRX run planning; no API or database access."""

import re
from dataclasses import dataclass
from datetime import date, timedelta


MARKETS = ("KOSPI", "KOSDAQ", "KONEX")


@dataclass(frozen=True)
class RunPlan:
    market: str
    start: date
    end: date
    tickers: tuple[str, ...]

    @property
    def calendar_days(self) -> int:
        return (self.end - self.start).days + 1

    def candidate_dates(self):
        """Yield calendar dates; R2 will identify actual KRX trading days."""
        for offset in range(self.calendar_days):
            yield self.start + timedelta(days=offset)


def build_plan(
    market: str, start: date, end: date, tickers: list[str]
) -> RunPlan:
    if market not in MARKETS:
        raise ValueError(f"market must be one of {', '.join(MARKETS)}")
    if start > end:
        raise ValueError("start date must not be after end date")
    if not tickers:
        raise ValueError("at least one ticker is required")
    if len(tickers) != len(set(tickers)):
        raise ValueError("duplicate tickers are not allowed")
    if any(not re.fullmatch(r"[0-9]{6}", ticker) for ticker in tickers):
        raise ValueError("tickers must contain exactly six digits")
    return RunPlan(market, start, end, tuple(tickers))
