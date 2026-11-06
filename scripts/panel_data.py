"""Build the pooled daily panel: per-symbol, market, cross-sectional and index features plus labels."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from preprocess_data import BASE_FEATURE_COLUMNS, RESOLUTION_CONFIG, WARMUP_ROWS, add_base_features


ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_DIRS = (ROOT / "data" / "cleaned" / "1D", ROOT / "data" / "extra" / "cleaned" / "1D")
INDEX_PATH = ROOT / "data" / "raw" / "index" / "1D" / "VNINDEX.csv"
WARMUP = 60
MIN_SYMBOLS_PER_DATE = 9
THRESHOLD = RESOLUTION_CONFIG["1D"]["threshold"]
FORWARD_HORIZONS = (3, 5, 10, 20)
EXTRA_RETURN_COLUMNS = ("r_gap", "r_intra", "r_oo", *(f"r_fwd{h}" for h in FORWARD_HORIZONS))

OWN_EXTRA_COLUMNS = (
    "ret_10", "ret_20", "ret_60", "volat_60", "ewm_vol10", "abs_ret_1", "max_abs_ret_5",
    "dist_high_60", "dist_low_60", "park_vol10", "vol_ratio_5_60", "weekday_sin", "weekday_cos",
)
MARKET_COLUMNS = (
    "mkt_ret_1", "mkt_ret_5", "mkt_ret_20", "mkt_volat_5", "mkt_volat_20", "mkt_disp",
    "mkt_breadth", "rel_ret_1", "rel_ret_5", "rel_ret_20",
)
RANK_SOURCES = ("ret_5", "ret_20", "volat_20", "vol_ratio", "atr14")
RANK_COLUMNS = tuple(f"xs_rank_{name}" for name in RANK_SOURCES)
INDEX_COLUMNS = (
    "idx_ret_1", "idx_ret_5", "idx_ret_20", "idx_volat_20", "idx_dist_high_60",
    "idx_vol_ratio", "rel_idx_ret_5", "rel_idx_ret_20",
)
FEATURE_SETS = {
    "base": tuple(BASE_FEATURE_COLUMNS),
    "full": (*BASE_FEATURE_COLUMNS, *OWN_EXTRA_COLUMNS, *MARKET_COLUMNS, *RANK_COLUMNS),
    "full_idx": (*BASE_FEATURE_COLUMNS, *OWN_EXTRA_COLUMNS, *MARKET_COLUMNS, *RANK_COLUMNS, *INDEX_COLUMNS),
}


def load_universe(directories: tuple[Path, ...] = UNIVERSE_DIRS) -> dict[str, pd.DataFrame]:
    universe = {}
    for directory in directories:
        for path in sorted(directory.glob("*.csv")):
            if path.stem.endswith("summary"):
                continue
            frame = pd.read_csv(path, parse_dates=["time"]).sort_values("time").reset_index(drop=True)
            universe[path.stem] = frame
    return universe


def load_index(path: Path = INDEX_PATH) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["time"]).sort_values("time").reset_index(drop=True)


def own_features(data: pd.DataFrame) -> pd.DataFrame:
    featured = add_base_features(data)
    close, high, low, volume = featured["close"], featured["high"], featured["low"], featured["volume"]
    log_return = np.log(close / close.shift(1))
    for lag in (10, 20, 60):
        featured[f"ret_{lag}"] = np.log(close / close.shift(lag))
    featured["volat_60"] = log_return.rolling(60).std(ddof=0)
    featured["ewm_vol10"] = np.sqrt((log_return**2).ewm(span=10, adjust=False).mean())
    featured["abs_ret_1"] = log_return.abs()
    featured["max_abs_ret_5"] = log_return.abs().rolling(5).max()
    featured["dist_high_60"] = close / close.rolling(60).max() - 1
    featured["dist_low_60"] = close / close.rolling(60).min() - 1
    featured["park_vol10"] = np.sqrt((np.log(high / low) ** 2).rolling(10).mean() / (4 * np.log(2)))
    featured["vol_ratio_5_60"] = volume.rolling(5).mean() / volume.rolling(60).mean()
    weekday_angle = 2 * np.pi * featured["time"].dt.weekday / 5
    featured["weekday_sin"] = np.sin(weekday_angle)
    featured["weekday_cos"] = np.cos(weekday_angle)
    featured["r_next"] = np.log(close.shift(-1) / close)
    next_open = featured["open"].shift(-1)
    featured["r_gap"] = np.log(next_open / close)
    featured["r_intra"] = np.log(close.shift(-1) / next_open)
    featured["r_oo"] = np.log(featured["open"].shift(-2) / next_open)
    for horizon in FORWARD_HORIZONS:
        featured[f"r_fwd{horizon}"] = np.log(close.shift(-horizon) / close)
    return featured


def index_features(index: pd.DataFrame) -> pd.DataFrame:
    close, volume = index["close"], index["volume"]
    log_return = np.log(close / close.shift(1))
    return pd.DataFrame(
        {
            "time": index["time"],
            "idx_ret_1": log_return,
            "idx_ret_5": np.log(close / close.shift(5)),
            "idx_ret_20": np.log(close / close.shift(20)),
            "idx_volat_20": log_return.rolling(20).std(ddof=0),
            "idx_dist_high_60": close / close.rolling(60).max() - 1,
            "idx_vol_ratio": volume / volume.rolling(20).mean(),
        }
    )


def add_market_features(panel: pd.DataFrame) -> pd.DataFrame:
    by_date = panel.groupby("time")
    market = pd.DataFrame(
        {
            "mkt_ret_1": by_date["ret_1"].mean(),
            "mkt_ret_5": by_date["ret_5"].mean(),
            "mkt_ret_20": by_date["ret_20"].mean(),
            "mkt_disp": by_date["ret_1"].std(ddof=0),
            "mkt_breadth": by_date["ret_1"].apply(lambda values: (values > 0).mean()),
        }
    )
    market["mkt_volat_5"] = market["mkt_ret_1"].rolling(5).std(ddof=0)
    market["mkt_volat_20"] = market["mkt_ret_1"].rolling(20).std(ddof=0)
    panel = panel.merge(market, left_on="time", right_index=True, how="left")
    for lag in (1, 5, 20):
        panel[f"rel_ret_{lag}"] = panel[f"ret_{lag}"] - panel[f"mkt_ret_{lag}"]
    ranks = panel.groupby("time")[list(RANK_SOURCES)].rank(pct=True)
    ranks.columns = RANK_COLUMNS
    return pd.concat([panel, ranks], axis=1)


def add_index_features(panel: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    panel = pd.merge_asof(
        panel.sort_values("time"), index_features(index).sort_values("time"), on="time", direction="backward"
    )
    panel["rel_idx_ret_5"] = panel["ret_5"] - panel["idx_ret_5"]
    panel["rel_idx_ret_20"] = panel["ret_20"] - panel["idx_ret_20"]
    return panel


def add_labels(panel: pd.DataFrame) -> pd.DataFrame:
    panel["label_abs"] = np.select(
        [panel["r_next"] > THRESHOLD, panel["r_next"] < -THRESHOLD], [1, -1], default=0
    )
    by_date = panel.groupby("time")["r_next"]
    panel["r_rel"] = panel["r_next"] - by_date.transform("mean")
    pct_rank = by_date.rank(pct=True)
    panel["label_rel"] = np.select([pct_rank > 2 / 3, pct_rank <= 1 / 3], [1, -1], default=0)
    for horizon in FORWARD_HORIZONS:
        horizon_rank = panel.groupby("time")[f"r_fwd{horizon}"].rank(pct=True)
        panel[f"label_rel{horizon}"] = np.select([horizon_rank > 2 / 3, horizon_rank <= 1 / 3], [1, -1], default=0)
        panel.loc[panel[f"r_fwd{horizon}"].isna(), f"label_rel{horizon}"] = np.nan
    enough = by_date.transform("size") >= MIN_SYMBOLS_PER_DATE
    return panel[enough]


def featurize(universe: dict[str, pd.DataFrame], max_date: pd.Timestamp | None = None) -> pd.DataFrame:
    frames = []
    for symbol, data in universe.items():
        if max_date is not None:
            data = data[data["time"] <= max_date]
        featured = own_features(data).iloc[WARMUP:]
        featured.insert(1, "symbol", symbol)
        frames.append(featured)
    return add_market_features(pd.concat(frames, ignore_index=True))


def build_panel(
    universe: dict[str, pd.DataFrame], index: pd.DataFrame, max_date: pd.Timestamp | None = None
) -> pd.DataFrame:
    if max_date is not None:
        index = index[index["time"] <= max_date]
    panel = add_index_features(featurize(universe, max_date), index)
    panel = panel.dropna(subset=list(FEATURE_SETS["full_idx"]))
    panel = panel.replace([np.inf, -np.inf], np.nan).dropna(subset=list(FEATURE_SETS["full_idx"]))
    labeled = panel.dropna(subset=["r_next"]).copy()
    labeled = add_labels(labeled)
    keep = [
        "time", "symbol", "close", *FEATURE_SETS["full_idx"], "r_next", "r_rel", "label_abs", "label_rel",
        *EXTRA_RETURN_COLUMNS, *(f"label_rel{h}" for h in FORWARD_HORIZONS),
    ]
    return labeled[keep].sort_values(["time", "symbol"]).reset_index(drop=True)


def verify_no_lookahead(universe, index, panel: pd.DataFrame, checks: int = 6, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    dates = panel["time"].drop_duplicates().sort_values().to_numpy()
    for cutoff in rng.choice(dates[300:-1], size=checks, replace=False):
        cutoff = pd.Timestamp(cutoff)
        truncated = build_panel(universe, index, max_date=cutoff)
        columns = list(FEATURE_SETS["full_idx"])
        earlier = truncated[truncated["time"] < cutoff].merge(
            panel[panel["time"] < cutoff], on=["time", "symbol"], suffixes=("_cut", "_full")
        )
        gaps = np.abs(
            earlier[[f"{c}_cut" for c in columns]].to_numpy() - earlier[[f"{c}_full" for c in columns]].to_numpy()
        ).max()
        if not gaps < 1e-9:
            raise AssertionError(f"Features differ when future data is removed (cutoff {cutoff.date()}, gap {gaps})")
        print(f"cutoff {cutoff.date()}: {len(earlier)} rows identical")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "extra" / "panel_1D.csv.gz")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    universe, index = load_universe(), load_index()
    panel = build_panel(universe, index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    print(f"{len(panel)} rows, {panel['symbol'].nunique()} symbols, {panel['time'].min().date()} to {panel['time'].max().date()}")
    print(panel["label_abs"].value_counts(normalize=True).round(3).sort_index().to_dict(),
          panel["label_rel"].value_counts(normalize=True).round(3).sort_index().to_dict())
    if args.verify:
        verify_no_lookahead(universe, index, panel)


if __name__ == "__main__":
    main()
