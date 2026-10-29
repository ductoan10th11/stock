"""Clean every OHLCV resolution without modifying the raw data."""

import argparse
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


SYMBOLS = ("TCB", "CTG", "VNM", "ACB")
RESOLUTIONS = ("1", "5", "15", "30", "1H", "1D")
BAR_MINUTES = {"1": 1, "5": 5, "15": 15, "30": 30, "1H": 60}
REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = (*PRICE_COLUMNS, "volume")
MARKET_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
MARKET_CLOSE = time(15, 0)
ROOT = Path(__file__).resolve().parent


def incomplete_candle_mask(
    timestamps: pd.Series,
    resolution: str,
    now: datetime,
) -> pd.Series:
    local_now = now.astimezone(MARKET_TIMEZONE)
    today = timestamps.dt.date == local_now.date()

    if resolution == "1D":
        return today & (local_now.time().replace(tzinfo=None) < MARKET_CLOSE)

    if resolution not in BAR_MINUTES:
        raise ValueError(f"Unsupported resolution: {resolution}")

    local_now_naive = local_now.replace(tzinfo=None)
    bar_end = timestamps + timedelta(minutes=BAR_MINUTES[resolution])
    return today & (bar_end > local_now_naive)


def clean_ohlcv_data(
    data: pd.DataFrame,
    resolution: str,
    now: datetime | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    cleaned = data.loc[:, REQUIRED_COLUMNS].copy()
    rows_before = len(cleaned)
    cleaned["time"] = pd.to_datetime(cleaned["time"], errors="coerce")
    cleaned[list(NUMERIC_COLUMNS)] = cleaned[list(NUMERIC_COLUMNS)].apply(
        pd.to_numeric, errors="coerce"
    )

    invalid_required = cleaned[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    missing_rows_removed = int(invalid_required.sum())
    cleaned = cleaned.loc[~invalid_required]

    invalid_price = (cleaned[list(PRICE_COLUMNS)] <= 0).any(axis=1)
    invalid_price_rows_removed = int(invalid_price.sum())
    cleaned = cleaned.loc[~invalid_price]

    invalid_volume = cleaned["volume"] <= 0
    invalid_volume_rows_removed = int(invalid_volume.sum())
    cleaned = cleaned.loc[~invalid_volume]

    cleaned = cleaned.sort_values("time", kind="stable")
    duplicate_rows_merged = int(cleaned.duplicated("time").sum())
    cleaned = cleaned.groupby("time", as_index=False, sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )

    bad_ohlc = (
        (cleaned["open"] > cleaned["high"])
        | (cleaned["close"] > cleaned["high"])
        | (cleaned["open"] < cleaned["low"])
        | (cleaned["close"] < cleaned["low"])
    )
    ohlc_rows_corrected = int(bad_ohlc.sum())
    cleaned["high"] = cleaned[["open", "high", "close"]].max(axis=1)
    cleaned["low"] = cleaned[["open", "low", "close"]].min(axis=1)

    current_time = now or datetime.now(MARKET_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=MARKET_TIMEZONE)
    incomplete = incomplete_candle_mask(cleaned["time"], resolution, current_time)
    incomplete_rows_removed = int(incomplete.sum())
    cleaned = cleaned.loc[~incomplete].reset_index(drop=True)

    cleaned["volume"] = cleaned["volume"].astype("int64")
    time_format = "%Y-%m-%d" if resolution == "1D" else "%Y-%m-%d %H:%M"
    cleaned["time"] = cleaned["time"].dt.strftime(time_format)

    if cleaned["time"].duplicated().any():
        raise ValueError("Duplicate timestamps remain after cleaning")
    if not cleaned["time"].is_monotonic_increasing:
        raise ValueError("Timestamps are not sorted after cleaning")
    if cleaned.isna().any().any():
        raise ValueError("Missing values remain after cleaning")
    if (
        (cleaned["open"] > cleaned["high"])
        | (cleaned["close"] > cleaned["high"])
        | (cleaned["open"] < cleaned["low"])
        | (cleaned["close"] < cleaned["low"])
    ).any():
        raise ValueError("Invalid OHLC rows remain after cleaning")

    summary = {
        "rows_before": rows_before,
        "missing_rows_removed": missing_rows_removed,
        "invalid_price_rows_removed": invalid_price_rows_removed,
        "invalid_volume_rows_removed": invalid_volume_rows_removed,
        "duplicate_rows_merged": duplicate_rows_merged,
        "ohlc_rows_corrected": ohlc_rows_corrected,
        "incomplete_rows_removed": incomplete_rows_removed,
        "rows_after": len(cleaned),
    }
    return cleaned, summary


def clean_daily_data(
    data: pd.DataFrame,
    now: datetime | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    return clean_ohlcv_data(data, "1D", now)


def clean_files(
    input_root: Path,
    output_root: Path,
    resolutions: tuple[str, ...],
    symbols: tuple[str, ...],
) -> pd.DataFrame:
    summaries = []

    for resolution in resolutions:
        input_dir = input_root / resolution
        output_dir = output_root / resolution
        output_dir.mkdir(parents=True, exist_ok=True)
        resolution_summaries = []

        for symbol in symbols:
            input_path = input_dir / f"{symbol}.csv"
            if not input_path.is_file():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            cleaned, summary = clean_ohlcv_data(pd.read_csv(input_path), resolution)
            cleaned.to_csv(output_dir / input_path.name, index=False)
            row = {"resolution": resolution, "symbol": symbol, **summary}
            summaries.append(row)
            resolution_summaries.append(row)
            print(
                f"{resolution:>2} {symbol}: {summary['rows_before']} -> "
                f"{summary['rows_after']} rows; merged "
                f"{summary['duplicate_rows_merged']} duplicate; corrected "
                f"{summary['ohlc_rows_corrected']} OHLC"
            )

        pd.DataFrame(resolution_summaries).to_csv(
            output_dir / "cleaning_summary.csv", index=False
        )

    audit = pd.DataFrame(summaries)
    output_root.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_root / "cleaning_summary.csv", index=False)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "cleaned")
    parser.add_argument("--resolutions", nargs="+", default=list(RESOLUTIONS))
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_files(
        args.input_root,
        args.output_root,
        tuple(args.resolutions),
        tuple(args.symbols),
    )


if __name__ == "__main__":
    main()
