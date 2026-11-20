"""CLI for KRX ingestion. R1 supports planning only."""

import argparse
from datetime import date, datetime

from pipeline.krx.plan import MARKETS, RunPlan, build_plan


def parse_date(value: str) -> date:
    try:
        if len(value) != 8 or not value.isdigit():
            raise ValueError("invalid date format")
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYYMMDD") from exc


def render_plan(plan: RunPlan) -> str:
    lines = [
        f"KRX {plan.market} dry-run",
        f"├─ dates: {plan.start:%Y%m%d}..{plan.end:%Y%m%d} "
        f"({plan.calendar_days} calendar days; trading days not checked)",
        f"├─ tickers: {', '.join(plan.tickers)}",
        "└─ candidate jobs:",
    ]
    for day in plan.candidate_dates():
        lines.append(
            f"   ├─ {day:%Y%m%d}: one market snapshot; "
            f"{len(plan.tickers)} investor trading requests"
        )
    lines.append("No API requests or database writes were made.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan KRX market data ingestion.")
    parser.add_argument("--market", required=True, choices=MARKETS)
    parser.add_argument("--start", required=True, type=parse_date, help="YYYYMMDD")
    parser.add_argument("--end", required=True, type=parse_date, help="YYYYMMDD")
    parser.add_argument("--tickers", nargs="+", required=True, help="six-digit tickers")
    parser.add_argument("--dry-run", action="store_true", help="print plan without I/O")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("R1 supports --dry-run only")
    try:
        plan = build_plan(args.market, args.start, args.end, args.tickers)
    except ValueError as exc:
        parser.error(str(exc))
    print(render_plan(plan))


if __name__ == "__main__":
    main()
