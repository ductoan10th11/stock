"""Compare the candidate models on the walk-forward folds and report the chosen one with bootstrap intervals."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from preprocess_data import SYMBOLS
from train_models import RANDOM_STATE


ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP_RUNS = 10_000
CANDIDATE_VARIANT = "all_default"
CANDIDATES = ("logistic", "random_forest", "xgboost")
FINAL_MODEL = "random_forest"


def load_folds(results_dir: Path) -> pd.DataFrame:
    tuning = pd.read_csv(results_dir / "tuning" / "fold_metrics.csv")
    candidates = tuning[tuning["variant"] == CANDIDATE_VARIANT].drop(columns="variant")
    baseline = pd.read_csv(results_dir / "fold_metrics.csv")
    baselines = baseline[baseline["model"].isin(["random", "majority"])]
    return pd.concat([candidates, baselines], ignore_index=True)


def wide_metric(folds: pd.DataFrame, metric: str) -> pd.DataFrame:
    return folds.pivot_table(index=["symbol", "fold"], columns="model", values=metric)


def bootstrap_mean_ci(values: pd.Series, rng: np.random.Generator) -> tuple[float, float, float]:
    groups = [group.to_numpy() for _, group in values.groupby(level="symbol")]
    totals = sum(
        group[rng.integers(0, len(group), (BOOTSTRAP_RUNS, len(group)))].sum(axis=1)
        for group in groups
    )
    means = totals / len(values)
    low, high = np.percentile(means, [2.5, 97.5])
    return values.mean(), low, high


def format_ci(estimate: tuple[float, float, float]) -> str:
    mean, low, high = estimate
    return f"{mean:+.3f} [{low:+.3f}; {high:+.3f}]"


def compare_candidates(folds: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    f1 = wide_metric(folds, "f1_macro")
    auc = wide_metric(folds, "roc_auc")
    rows = []
    for model in CANDIDATES:
        subset = folds[folds["model"] == model]
        rows.append(
            {
                "model": model,
                "f1_mean": f1[model].mean(),
                "f1_std": f1[model].std(),
                "auc_mean": auc[model].mean(),
                "f1_above_random": (f1[model] > f1["random"]).mean(),
                "auc_above_half": (auc[model] > 0.5).mean(),
                "train_f1": subset["train_f1_macro"].mean(),
                "fit_seconds": subset["fit_seconds"].mean(),
                "f1_minus_random": format_ci(bootstrap_mean_ci(f1[model] - f1["random"], rng)),
                "f1_minus_final": (
                    "-" if model == FINAL_MODEL
                    else format_ci(bootstrap_mean_ci(f1[model] - f1[FINAL_MODEL], rng))
                ),
            }
        )
    return pd.DataFrame(rows)


def report_final_by_symbol(folds: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    f1 = wide_metric(folds, "f1_macro")
    auc = wide_metric(folds, "roc_auc")
    accuracy = wide_metric(folds, "accuracy")
    rows = []
    for symbol in (*SYMBOLS, "ALL"):
        keep = np.ones(len(f1), dtype=bool) if symbol == "ALL" else f1.index.get_level_values("symbol") == symbol
        f1_s, auc_s, acc_s = f1[keep], auc[keep], accuracy[keep]
        rows.append(
            {
                "symbol": symbol,
                "folds": len(f1_s),
                "accuracy": acc_s[FINAL_MODEL].mean(),
                "f1_macro": f1_s[FINAL_MODEL].mean(),
                "roc_auc": auc_s[FINAL_MODEL].mean(),
                "f1_minus_random": format_ci(bootstrap_mean_ci(f1_s[FINAL_MODEL] - f1_s["random"], rng)),
                "accuracy_minus_majority": format_ci(
                    bootstrap_mean_ci(acc_s[FINAL_MODEL] - acc_s["majority"], rng)
                ),
                "auc_minus_half": format_ci(bootstrap_mean_ci(auc_s[FINAL_MODEL] - 0.5, rng)),
            }
        )
    return pd.DataFrame(rows)


def report_final_by_year(folds: pd.DataFrame) -> pd.DataFrame:
    final = folds[folds["model"] == FINAL_MODEL].set_index(["symbol", "fold"])
    random = folds[folds["model"] == "random"].set_index(["symbol", "fold"])
    table = pd.DataFrame(
        {
            "year": pd.to_datetime(final["test_start"]).dt.year,
            "f1_final": final["f1_macro"],
            "f1_random": random["f1_macro"],
            "auc_final": final["roc_auc"],
        }
    )
    summary = table.groupby("year").agg(
        folds=("f1_final", "size"),
        f1_final=("f1_final", "mean"),
        f1_random=("f1_random", "mean"),
        auc_final=("auc_final", "mean"),
    )
    return summary.assign(f1_minus_random=summary["f1_final"] - summary["f1_random"]).reset_index()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results" / "1D")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    folds = load_folds(args.results_dir)
    rng = np.random.default_rng(RANDOM_STATE)
    candidates = compare_candidates(folds, rng)
    by_symbol = report_final_by_symbol(folds, rng)
    by_year = report_final_by_year(folds)

    output_dir = args.results_dir / "final"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(output_dir / "candidate_comparison.csv", index=False)
    by_symbol.to_csv(output_dir / "final_by_symbol.csv", index=False)
    by_year.to_csv(output_dir / "final_by_year.csv", index=False)

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", None)
    for table in (candidates, by_symbol, by_year):
        print(table.round(4).to_string(index=False), end="\n\n")


if __name__ == "__main__":
    main()
