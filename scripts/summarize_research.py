"""Collect experiment metrics into one table and compare against the original four symbols."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from panel_experiments import (
    CONFIRM_START, FLAT, RANDOM_STATE, TRADING_DAYS, UP, alpha_beta, daily_rank_ic, date_folds, fold_scores,
    top_k_portfolio,
)


ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_SYMBOLS = ("TCB", "CTG", "VNM", "ACB")
COMPARED_CONFIGS = ("persym_abs_full", "pooled_abs_full", "pooled_rel_full")
COMPARED_MODELS = ("random_forest", "xgboost", "ensemble3")
MIN_SYMBOLS_PER_DATE = 3
TIMING_CONFIGS = ("pooled_abs_full", "pooled_rel_full")
TIMING_MODELS = ("xgboost", "ensemble3")
EXECUTION_RETURNS = {"close_to_close": "r_next", "next_open_to_next_open": "r_oo", "intraday_only": "r_intra"}


def collect_metrics(research_dir: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in sorted(research_dir.glob("*/metrics.csv"))]
    metrics = pd.concat(frames, ignore_index=True)
    metrics["horizon"] = metrics["horizon"].fillna(1).astype(int)
    return metrics


def original_symbols_comparison(research_dir: Path) -> pd.DataFrame:
    rows = []
    for name in COMPARED_CONFIGS:
        path = research_dir / name / "oof.csv.gz"
        if not path.is_file():
            continue
        oof = pd.read_csv(path, parse_dates=["time", "test_start"])
        oof = oof[oof["symbol"].isin(ORIGINAL_SYMBOLS) & oof["model"].isin(COMPARED_MODELS)]
        oof = oof.assign(
            period=np.where(oof["test_start"] >= CONFIRM_START, "confirm", "dev"),
            score=oof["p_up"] - oof["p_down"],
        )
        for (model, period), frame in oof.groupby(["model", "period"]):
            f1, auc, baseline = fold_scores(frame, np.random.default_rng(RANDOM_STATE))
            directional = frame["y"] != FLAT
            enough = frame.groupby("time")["symbol"].transform("size") >= MIN_SYMBOLS_PER_DATE
            ic = daily_rank_ic(frame[enough], "r_next")
            rows.append(
                {
                    "config": name, "model": model, "period": period, "f1": f1, "f1_random": baseline,
                    "auc_up_vs_down": roc_auc_score(frame["y"][directional] == UP, frame["score"][directional]),
                    "rank_ic": ic.mean(),
                }
            )
    return pd.DataFrame(rows)


def identity_only_ic(panel: pd.DataFrame) -> pd.DataFrame:
    test_frames = []
    for fold, train_end, test_start, test_end in date_folds(panel):
        train = panel[panel["time"] <= train_end]
        test = panel[(panel["time"] >= test_start) & (panel["time"] <= test_end)].copy()
        test["mean_return"] = test["symbol"].map(train.groupby("symbol")["r_next"].mean())
        test["mean_direction"] = test["symbol"].map(train.groupby("symbol")["label_abs"].mean())
        test["test_start"] = test_start
        test_frames.append(test)
    dev = pd.concat(test_frames)
    dev = dev[dev["test_start"] < CONFIRM_START]
    rows = []
    for predictor in ("mean_return", "mean_direction"):
        ic = daily_rank_ic(dev.assign(score=dev[predictor]), "r_next")
        rows.append({"predictor": predictor, "rank_ic": ic.mean(), "t_stat": ic.mean() / ic.std() * np.sqrt(len(ic)),
                     "days": len(ic)})
    return pd.DataFrame(rows)


def single_feature_ic(panel: pd.DataFrame, features: tuple[str, ...] = ("ret_3", "lower_shadow", "upper_shadow")):
    rows, by_year = [], {}
    for feature in features:
        ic = daily_rank_ic(panel[["time", "r_next", feature]].rename(columns={feature: "score"}), "r_next")
        rows.append({"feature": feature, "rank_ic": ic.mean(), "t_stat": ic.mean() / ic.std() * np.sqrt(len(ic))})
        by_year[feature] = ic.groupby(ic.index.year).mean()
    return pd.DataFrame(rows), pd.DataFrame(by_year)


def demeaned_score_ic(research_dir: Path, name: str = "pooled_abs_base", model: str = "xgboost") -> pd.DataFrame:
    oof = pd.read_csv(research_dir / name / "oof.csv.gz", parse_dates=["time", "test_start"])
    frame = oof[(oof["model"] == model) & (oof["test_start"] < CONFIRM_START)].sort_values(["symbol", "time"]).copy()
    frame["score"] = frame["p_up"] - frame["p_down"]
    past_mean = frame.groupby("symbol")["score"].transform(lambda s: s.shift(1).expanding().mean())
    frame = frame[past_mean.notna()].assign(score_demeaned=lambda x: x["score"] - past_mean[x.index])
    raw = daily_rank_ic(frame, "r_next")
    demeaned = daily_rank_ic(frame.assign(score=frame["score_demeaned"]), "r_next")
    return pd.DataFrame([{"config": name, "model": model, "ic_raw": raw.mean(), "ic_demeaned": demeaned.mean()}])


def execution_timing(research_dir: Path, panel: pd.DataFrame) -> pd.DataFrame:
    returns = panel[["time", "symbol", "r_gap", "r_intra", "r_oo"]]
    rows = []
    for name in TIMING_CONFIGS:
        oof = pd.read_csv(research_dir / name / "oof.csv.gz", parse_dates=["time", "test_start"])
        for model in TIMING_MODELS:
            frame = oof[(oof["model"] == model) & (oof["test_start"] < CONFIRM_START)].merge(
                returns, on=["time", "symbol"], how="left"
            )
            frame["score"] = frame["p_up"] - frame["p_down"]
            row = {"config": name, "model": model}
            for target in ("r_next", "r_gap", "r_intra", "r_oo"):
                row[f"ic_{target}"] = daily_rank_ic(frame.dropna(subset=[target]), target).mean()
            for label, column in EXECUTION_RETURNS.items():
                book = top_k_portfolio(frame.dropna(subset=[column]).assign(r_next=lambda x, c=column: x[c]))
                row[f"gross_alpha_{label}"] = alpha_beta(
                    book["gross"].to_numpy(), book["benchmark"].to_numpy(), TRADING_DAYS)[0]
                row[f"net_alpha_{label}"] = alpha_beta(
                    book["net"].to_numpy(), book["benchmark"].to_numpy(), TRADING_DAYS)[0]
            rows.append(row)
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-dir", type=Path, default=ROOT / "results" / "research")
    parser.add_argument("--panel", type=Path, default=ROOT / "data" / "extra" / "panel_1D.csv.gz")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.panel.is_file():
        panel = pd.read_csv(args.panel, parse_dates=["time"]).sort_values(["time", "symbol"]).reset_index(drop=True)
        identity = identity_only_ic(panel)
        timing = execution_timing(args.research_dir, panel)
        features, features_by_year = single_feature_ic(panel)
        demeaned = demeaned_score_ic(args.research_dir)
        identity.to_csv(args.research_dir / "identity_baseline.csv", index=False)
        features.to_csv(args.research_dir / "single_feature_ic.csv", index=False)
        features_by_year.to_csv(args.research_dir / "single_feature_ic_by_year.csv")
        demeaned.to_csv(args.research_dir / "demeaned_score_ic.csv", index=False)
        print(features.round(3).to_string(index=False), end="\n\n")
        print(features_by_year.round(3).to_string(), end="\n\n")
        print(demeaned.round(3).to_string(index=False), end="\n\n")
        timing.to_csv(args.research_dir / "execution_timing.csv", index=False)
        print(identity.round(3).to_string(index=False), end="\n\n")
        print(timing.round(3).T.to_string(header=False), end="\n\n")
    metrics = collect_metrics(args.research_dir)
    metrics.to_csv(args.research_dir / "summary.csv", index=False)
    comparison = original_symbols_comparison(args.research_dir)
    if len(comparison):
        comparison.to_csv(args.research_dir / "original_symbols_comparison.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)
    columns = ["name", "horizon", "model", "f1", "f1_random", "auc_up_vs_down", "auc_flat", "ic_rel", "ic_rel_t",
               "alpha_gross_ann", "alpha_net_ann", "alpha_ci_low", "alpha_ci_high", "buy_turnover_per_day",
               "sticky_alpha_net_ann", "sticky_alpha_ci_low", "sticky_alpha_ci_high", "sticky_buy_turnover"]
    for period in ("dev", "confirm"):
        subset = metrics[(metrics["period"] == period) & metrics["model"].isin(["xgboost", "ensemble3"])]
        print(f"\n{period}")
        print(subset[columns].sort_values(["name", "model"]).round(3).to_string(index=False))
    if len(comparison):
        print("\noriginal four symbols")
        print(comparison.sort_values(["period", "model", "config"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
