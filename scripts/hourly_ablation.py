"""Separate time-of-day structure from indicator skill on intraday walk-forward folds."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.naive_bayes import CategoricalNB

from preprocess_data import BASE_FEATURE_COLUMNS, TIME_FEATURE_COLUMNS, walk_forward_splits
from select_final_model import bootstrap_mean_ci, format_ci
from train_models import CLASSES, RANDOM_STATE, build_models, score_fold


ROOT = Path(__file__).resolve().parent.parent
FEATURE_SETS = {
    "base25": list(BASE_FEATURE_COLUMNS),
    "time5": list(TIME_FEATURE_COLUMNS),
    "base25+time5": [*BASE_FEATURE_COLUMNS, *TIME_FEATURE_COLUMNS],
}
MODEL_NAMES = ("logistic", "random_forest")
HOUR_PRIOR = "hour_prior"
COMPARISONS = (
    ("logistic:base25+time5", HOUR_PRIOR),
    ("random_forest:base25+time5", HOUR_PRIOR),
    ("logistic:base25+time5", "logistic:time5"),
    ("logistic:base25", HOUR_PRIOR),
    ("random_forest:base25", HOUR_PRIOR),
)


def evaluate_symbol(symbol: str, resolution: str, processed_root: Path):
    data = pd.read_csv(processed_root / resolution / f"{symbol}.csv", parse_dates=["time"])
    y = data["label"].to_numpy() + 1
    hours = data["time"].dt.hour.to_numpy()
    hour_codes = (hours - hours.min()).reshape(-1, 1)
    rows, probabilities = [], []

    for fold, (train_idx, test_idx) in enumerate(walk_forward_splits(len(data), resolution), start=1):
        predictions = {
            HOUR_PRIOR: CategoricalNB(min_categories=int(hour_codes.max()) + 1)
            .fit(hour_codes[train_idx], y[train_idx])
            .predict_proba(hour_codes[test_idx])
        }
        for set_name, columns in FEATURE_SETS.items():
            features = data[columns].to_numpy()
            for model_name in MODEL_NAMES:
                model = build_models()[model_name].fit(features[train_idx], y[train_idx])
                predictions[f"{model_name}:{set_name}"] = model.predict_proba(features[test_idx])
        for variant, proba in predictions.items():
            rows.append(
                {"symbol": symbol, "fold": fold, "variant": variant,
                 **score_fold(y[test_idx], CLASSES[proba.argmax(axis=1)], proba)}
            )
            probabilities.append(
                pd.DataFrame(
                    {"symbol": symbol, "variant": variant, "y": y[test_idx],
                     "p_down": proba[:, 0], "p_flat": proba[:, 1], "p_up": proba[:, 2]}
                )
            )
    return pd.DataFrame(rows), pd.concat(probabilities, ignore_index=True)


def summarize(folds: pd.DataFrame, probabilities: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant, frame in probabilities.groupby("variant"):
        up_down, flat = [], []
        for _, symbol_frame in frame.groupby("symbol"):
            directional = symbol_frame["y"] != 1
            up_down.append(
                roc_auc_score(
                    symbol_frame["y"][directional] == 2,
                    (symbol_frame["p_up"] - symbol_frame["p_down"])[directional],
                )
            )
            flat.append(roc_auc_score(symbol_frame["y"] == 1, symbol_frame["p_flat"]))
        scores = folds[folds["variant"] == variant]
        rows.append(
            {"variant": variant, "f1_macro": scores["f1_macro"].mean(), "roc_auc": scores["roc_auc"].mean(),
             "auc_up_vs_down": np.mean(up_down), "auc_flat": np.mean(flat)}
        )
    return pd.DataFrame(rows)


def compare(folds: pd.DataFrame) -> pd.DataFrame:
    f1 = folds.pivot_table(index=["symbol", "fold"], columns="variant", values="f1_macro")
    auc = folds.pivot_table(index=["symbol", "fold"], columns="variant", values="roc_auc")
    rng = np.random.default_rng(RANDOM_STATE)
    return pd.DataFrame(
        [
            {"a": a, "b": b,
             "f1_a_minus_b": format_ci(bootstrap_mean_ci(f1[a] - f1[b], rng)),
             "auc_a_minus_b": format_ci(bootstrap_mean_ci(auc[a] - auc[b], rng))}
            for a, b in COMPARISONS
        ]
    )


def hourly_profile(symbols: list[str], resolution: str, processed_root: Path) -> pd.DataFrame:
    data = pd.concat(
        [pd.read_csv(processed_root / resolution / f"{s}.csv", parse_dates=["time"]) for s in symbols]
    )
    data["hour"] = data["time"].dt.hour
    grouped = data.groupby("hour")
    return pd.DataFrame(
        {
            "bars": grouped.size(),
            "mean_r_next_pct": grouped["r_next"].mean() * 100,
            "std_r_next_pct": grouped["r_next"].std() * 100,
            "flat_share": grouped["label"].apply(lambda x: (x == 0).mean()),
            "up_share_of_directional": grouped["label"].apply(lambda x: (x[x != 0] == 1).mean()),
        }
    ).reset_index()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", default="1H")
    parser.add_argument("--symbols", nargs="+")
    parser.add_argument("--processed-root", type=Path, default=ROOT / "data" / "extra" / "processed")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results" / "extra")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = args.symbols or sorted(
        p.stem for p in (args.processed_root / args.resolution).glob("*.csv")
        if p.stem != "preprocessing_summary"
    )
    results = [evaluate_symbol(s, args.resolution, args.processed_root) for s in symbols]
    folds = pd.concat([r[0] for r in results], ignore_index=True)
    probabilities = pd.concat([r[1] for r in results], ignore_index=True)

    output_dir = args.output_root / args.resolution
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(folds, probabilities)
    differences = compare(folds)
    profile = hourly_profile(symbols, args.resolution, args.processed_root)
    folds.to_csv(output_dir / "ablation_fold_metrics.csv", index=False)
    summary.to_csv(output_dir / "ablation_summary.csv", index=False)
    differences.to_csv(output_dir / "ablation_differences.csv", index=False)
    profile.to_csv(output_dir / "hourly_profile.csv", index=False)

    pd.set_option("display.width", 220)
    for table in (summary, differences, profile):
        print(table.round(4).to_string(index=False), end="\n\n")


if __name__ == "__main__":
    main()
