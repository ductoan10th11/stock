"""Score raw daily data quality per symbol; selection uses data quality only, never model results."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
MIN_ROWS = 2400
MAX_MISSING_SESSIONS = 3
MAX_INVALID_OHLC = 3
MAX_FLAT_CLOSE_SHARE = 0.10
HOSE_PRICE_LIMIT = 0.075
LIQUIDITY_WINDOW = 500
CALENDAR_COVERAGE = 0.8


def reference_calendar(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    counts = pd.concat(
        [pd.Series(1, index=f["time"].drop_duplicates()) for f in frames.values()], axis=1
    ).sum(axis=1)
    return counts.index[counts >= CALENDAR_COVERAGE * len(frames)]


def quality_row(symbol: str, data: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict:
    data = data.sort_values("time").drop_duplicates("time", keep="last")
    log_return = np.log(data["close"] / data["close"].shift(1))
    expected = calendar[calendar >= data["time"].iloc[0]]
    recent = data.tail(LIQUIDITY_WINDOW)
    return {
        "symbol": symbol,
        "rows": len(data),
        "first": data["time"].iloc[0].date(),
        "last": data["time"].iloc[-1].date(),
        "missing_sessions": int(len(expected.difference(pd.DatetimeIndex(data["time"])))),
        "zero_volume_days": int((data["volume"] <= 0).sum()),
        "invalid_ohlc": int(
            ((data["open"] > data["high"]) | (data["close"] > data["high"])
             | (data["open"] < data["low"]) | (data["close"] < data["low"])).sum()
        ),
        "flat_close_share": float((log_return == 0).mean()),
        "days_beyond_limit": int((log_return.abs() > HOSE_PRICE_LIMIT).sum()),
        "return_std": float(log_return.std()),
        "median_price": float(recent["close"].median()),
        "median_value_billion_vnd": float((recent["close"] * 1000 * recent["volume"]).median() / 1e9),
    }


def screen(raw_dir: Path, symbols: list[str]) -> pd.DataFrame:
    frames = {s: pd.read_csv(raw_dir / f"{s}.csv", parse_dates=["time"]) for s in symbols}
    calendar = reference_calendar(frames)
    table = pd.DataFrame([quality_row(s, frames[s], calendar) for s in symbols])
    table["eligible"] = (
        (table["rows"] >= MIN_ROWS)
        & (table["missing_sessions"] <= MAX_MISSING_SESSIONS)
        & (table["zero_volume_days"] == 0)
        & (table["invalid_ohlc"] <= MAX_INVALID_OHLC)
        & (table["days_beyond_limit"] == 0)
        & (table["flat_close_share"] < MAX_FLAT_CLOSE_SHARE)
    )
    return table.sort_values(
        ["eligible", "median_value_billion_vnd"], ascending=[False, False]
    ).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw" / "1D")
    parser.add_argument("--symbols", nargs="+")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "screening" / "symbol_quality.csv")
    parser.add_argument("--top", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = args.symbols or sorted(p.stem for p in args.raw_dir.glob("*.csv"))
    table = screen(args.raw_dir, symbols)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    pd.set_option("display.width", 220)
    print(table.round(4).to_string(index=False))
    selected = table.loc[table["eligible"], "symbol"].head(args.top).tolist()
    print(f"\nSelected by liquidity among eligible: {' '.join(selected)}")


if __name__ == "__main__":
    main()
