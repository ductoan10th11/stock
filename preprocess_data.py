"""Create leak-free features and three-class labels for every OHLCV resolution."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SYMBOLS = ("TCB", "CTG", "VNM", "ACB")
RESOLUTIONS = ("1", "5", "15", "30", "1H", "1D")
WARMUP_ROWS = 35
RESOLUTION_CONFIG = {
    "1": {"threshold": 0.0005, "train_initial": 9000, "test_size": 1125, "gap": 1},
    "5": {"threshold": 0.0010, "train_initial": 1800, "test_size": 225, "gap": 1},
    "15": {"threshold": 0.0015, "train_initial": 640, "test_size": 80, "gap": 1},
    "30": {"threshold": 0.0015, "train_initial": 315, "test_size": 45, "gap": 1},
    "1H": {"threshold": 0.0020, "train_initial": 1000, "test_size": 125, "gap": 1},
    "1D": {"threshold": 0.0050, "train_initial": 750, "test_size": 63, "gap": 1},
}
BASE_FEATURE_COLUMNS = (
    "close_sma5",
    "close_sma10",
    "close_sma20",
    "sma5_sma20",
    "close_ema12",
    "close_ema26",
    "macd",
    "macd_signal",
    "macd_hist",
    "rsi14",
    "bb_pctb",
    "bb_width",
    "ret_1",
    "ret_2",
    "ret_3",
    "ret_5",
    "body",
    "upper_shadow",
    "lower_shadow",
    "hl_range",
    "volat_5",
    "volat_20",
    "vol_ratio",
    "vol_chg",
    "atr14",
)
TIME_FEATURE_COLUMNS = (
    "time_sin",
    "time_cos",
    "weekday_sin",
    "weekday_cos",
    "is_first_bar",
)
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS


def feature_columns_for(resolution: str) -> tuple[str, ...]:
    if resolution not in RESOLUTION_CONFIG:
        raise ValueError(f"Unsupported resolution: {resolution}")
    if resolution == "1D":
        return BASE_FEATURE_COLUMNS
    return (*BASE_FEATURE_COLUMNS, *TIME_FEATURE_COLUMNS)


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()
    loss = -delta.clip(upper=0).ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + relative_strength)
    rsi = rsi.mask((gain == 0) & (loss == 0), 50)
    rsi = rsi.mask((gain > 0) & (loss == 0), 100)
    return rsi.where(gain.notna()) / 100


def add_base_features(data: pd.DataFrame) -> pd.DataFrame:
    featured = data.copy()
    close = featured["close"]
    volume = featured["volume"]

    sma5 = close.rolling(5, min_periods=5).mean()
    sma10 = close.rolling(10, min_periods=10).mean()
    sma20 = close.rolling(20, min_periods=20).mean()
    featured["close_sma5"] = close / sma5 - 1
    featured["close_sma10"] = close / sma10 - 1
    featured["close_sma20"] = close / sma20 - 1
    featured["sma5_sma20"] = sma5 / sma20 - 1

    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    featured["close_ema12"] = close / ema12 - 1
    featured["close_ema26"] = close / ema26 - 1
    featured["macd"] = (ema12 - ema26) / close
    featured["macd_signal"] = featured["macd"].ewm(
        span=9, adjust=False, min_periods=9
    ).mean()
    featured["macd_hist"] = featured["macd"] - featured["macd_signal"]
    featured["rsi14"] = wilder_rsi(close)

    rolling_std20 = close.rolling(20, min_periods=20).std(ddof=0)
    upper_band = sma20 + 2 * rolling_std20
    lower_band = sma20 - 2 * rolling_std20
    band_range = upper_band - lower_band
    featured["bb_pctb"] = ((close - lower_band) / band_range).where(
        band_range > 0, 0.5
    )
    featured["bb_width"] = band_range / sma20

    for lag in (1, 2, 3, 5):
        featured[f"ret_{lag}"] = np.log(close / close.shift(lag))

    featured["body"] = (featured["close"] - featured["open"]) / featured["open"]
    featured["upper_shadow"] = (
        featured["high"] - featured[["open", "close"]].max(axis=1)
    ) / close
    featured["lower_shadow"] = (
        featured[["open", "close"]].min(axis=1) - featured["low"]
    ) / close
    featured["hl_range"] = (featured["high"] - featured["low"]) / close
    featured["volat_5"] = featured["ret_1"].rolling(5, min_periods=5).std(ddof=0)
    featured["volat_20"] = featured["ret_1"].rolling(20, min_periods=20).std(ddof=0)
    featured["vol_ratio"] = volume / volume.rolling(20, min_periods=20).mean()
    featured["vol_chg"] = np.log(volume / volume.shift(1))

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            featured["high"] - featured["low"],
            (featured["high"] - previous_close).abs(),
            (featured["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    featured["atr14"] = true_range.rolling(14, min_periods=14).mean() / close
    return featured


def add_time_features(data: pd.DataFrame) -> pd.DataFrame:
    featured = data.copy()
    minutes = featured["time"].dt.hour * 60 + featured["time"].dt.minute
    time_angle = 2 * np.pi * minutes / (24 * 60)
    weekday_angle = 2 * np.pi * featured["time"].dt.weekday / 5
    featured["time_sin"] = np.sin(time_angle)
    featured["time_cos"] = np.cos(time_angle)
    featured["weekday_sin"] = np.sin(weekday_angle)
    featured["weekday_cos"] = np.cos(weekday_angle)
    featured["is_first_bar"] = (
        featured.groupby(featured["time"].dt.date, sort=False).cumcount() == 0
    ).astype("int8")
    return featured


def create_features(data: pd.DataFrame, resolution: str = "1D") -> pd.DataFrame:
    featured = add_base_features(data)
    if resolution != "1D":
        featured = add_time_features(featured)

    threshold = RESOLUTION_CONFIG[resolution]["threshold"]
    featured["r_next"] = np.log(featured["close"].shift(-1) / featured["close"])
    featured["label"] = np.select(
        [featured["r_next"] > threshold, featured["r_next"] < -threshold],
        [1, -1],
        default=0,
    )
    return featured


def preprocess_ohlcv_data(data: pd.DataFrame, resolution: str) -> pd.DataFrame:
    required = {"time", "open", "high", "low", "close", "volume"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if len(data) <= WARMUP_ROWS + 1:
        raise ValueError("Not enough rows for warm-up and next-bar label")

    source = data.loc[:, ["time", "open", "high", "low", "close", "volume"]].copy()
    source["time"] = pd.to_datetime(source["time"], errors="raise")
    source = source.sort_values("time", kind="stable").reset_index(drop=True)
    if source["time"].duplicated().any():
        raise ValueError("Input contains duplicate timestamps; run clean_data.py first")

    featured = create_features(source, resolution)
    processed = featured.iloc[WARMUP_ROWS:-1].copy()
    feature_columns = feature_columns_for(resolution)
    output_columns = ["time", "close", *feature_columns, "r_next", "label"]
    processed = processed.loc[:, output_columns].replace([np.inf, -np.inf], np.nan)
    if processed.isna().any().any():
        missing_columns = processed.columns[processed.isna().any()].tolist()
        raise ValueError(f"Missing feature values remain: {', '.join(missing_columns)}")

    time_format = "%Y-%m-%d" if resolution == "1D" else "%Y-%m-%d %H:%M"
    processed["time"] = processed["time"].dt.strftime(time_format)
    processed["label"] = processed["label"].astype("int8")
    if set(processed["label"].unique()) - {-1, 0, 1}:
        raise ValueError("Unexpected label values")
    if {"r_next", "label"} & set(feature_columns):
        raise ValueError("Future-looking columns must not be features")
    return processed.reset_index(drop=True)


def preprocess_daily_data(data: pd.DataFrame) -> pd.DataFrame:
    return preprocess_ohlcv_data(data, "1D")


def walk_forward_fold_count(rows: int, resolution: str) -> int:
    config = RESOLUTION_CONFIG[resolution]
    required = config["train_initial"] + config["gap"] + config["test_size"]
    if rows < required:
        return 0
    return 1 + (rows - required) // config["test_size"]


def walk_forward_splits(rows: int, resolution: str):
    config = RESOLUTION_CONFIG[resolution]
    train_initial = config["train_initial"]
    test_size = config["test_size"]
    gap = config["gap"]
    for test_start in range(train_initial + gap, rows - test_size + 1, test_size):
        train_indices = np.arange(0, test_start - gap)
        test_indices = np.arange(test_start, test_start + test_size)
        yield train_indices, test_indices


def preprocess_files(
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
        resolution_rows = []
        config = RESOLUTION_CONFIG[resolution]

        for symbol in symbols:
            input_path = input_dir / f"{symbol}.csv"
            if not input_path.is_file():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            processed = preprocess_ohlcv_data(pd.read_csv(input_path), resolution)
            processed.to_csv(output_dir / input_path.name, index=False)
            label_counts = processed["label"].value_counts().to_dict()
            row = {
                "resolution": resolution,
                "symbol": symbol,
                "rows": len(processed),
                "features": len(feature_columns_for(resolution)),
                "threshold": config["threshold"],
                "first_time": processed["time"].iloc[0],
                "last_time": processed["time"].iloc[-1],
                "decrease": int(label_counts.get(-1, 0)),
                "sideways": int(label_counts.get(0, 0)),
                "increase": int(label_counts.get(1, 0)),
                "train_initial": config["train_initial"],
                "test_size": config["test_size"],
                "gap": config["gap"],
                "folds": walk_forward_fold_count(len(processed), resolution),
            }
            summaries.append(row)
            resolution_rows.append(row)
            print(
                f"{resolution:>2} {symbol}: {row['rows']} rows, {row['features']} features, "
                f"labels -1/0/1 = {row['decrease']}/{row['sideways']}/{row['increase']}"
            )

        pd.DataFrame(resolution_rows).to_csv(
            output_dir / "preprocessing_summary.csv", index=False
        )

    summary = pd.DataFrame(summaries)
    output_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_root / "preprocessing_summary.csv", index=False)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=ROOT / "data" / "cleaned")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--resolutions", nargs="+", default=list(RESOLUTIONS))
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    preprocess_files(
        args.input_root,
        args.output_root,
        tuple(args.resolutions),
        tuple(args.symbols),
    )


if __name__ == "__main__":
    main()
