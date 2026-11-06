"""Walk-forward evaluation of the baselines and the three candidate models."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from preprocess_data import SYMBOLS, feature_columns_for, walk_forward_splits


ROOT = Path(__file__).resolve().parent.parent
RANDOM_STATE = 42
RANDOM_BASELINE_RUNS = 100
BUY_COST = np.log(1 + 0.0015)
SELL_COST = -np.log(1 - 0.0015 - 0.001)
TRADING_DAYS = 252
CLASSES = np.array([0, 1, 2])
UP, FLAT, DOWN = 2, 1, 0


def build_models() -> dict:
    return {
        "majority": DummyClassifier(strategy="most_frequent"),
        "logistic": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def score_fold(y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray | None) -> dict:
    auc = np.nan
    if proba is not None and len(np.unique(y_true)) == len(CLASSES):
        auc = roc_auc_score(y_true, proba, multi_class="ovr", average="macro", labels=CLASSES)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro", labels=CLASSES, zero_division=0),
        "roc_auc": auc,
    }


def backtest(y_pred: np.ndarray, r_next: np.ndarray) -> dict:
    position = (
        pd.Series(np.where(y_pred == UP, 1.0, np.where(y_pred == DOWN, 0.0, np.nan)))
        .ffill()
        .fillna(0.0)
        .to_numpy()
    )
    change = np.diff(position, prepend=0.0)
    buys = change == 1
    sells = change == -1
    log_return = position * r_next - buys * BUY_COST - sells * SELL_COST
    log_return[-1] -= position[-1] * SELL_COST
    daily_std = log_return.std(ddof=1)
    return {
        "total_return": np.expm1(log_return.sum()),
        "sharpe": log_return.mean() / daily_std * np.sqrt(TRADING_DAYS) if daily_std > 0 else np.nan,
        "trades": int(buys.sum()),
    }


def evaluate_symbol(symbol: str, resolution: str, processed_root: Path):
    data = pd.read_csv(processed_root / resolution / f"{symbol}.csv")
    features = data[list(feature_columns_for(resolution))].to_numpy()
    y = data["label"].to_numpy() + 1
    r_next = data["r_next"].to_numpy()
    times = data["time"].to_numpy()

    feature_names = feature_columns_for(resolution)
    fold_rows, prediction_frames, importance_rows = [], [], []
    test_blocks, random_draws = [], []
    rng = np.random.default_rng(RANDOM_STATE)

    for fold, (train_idx, test_idx) in enumerate(walk_forward_splits(len(data), resolution), start=1):
        base = {
            "symbol": symbol, "fold": fold, "train_size": len(train_idx),
            "test_start": times[test_idx[0]], "test_end": times[test_idx[-1]],
        }
        test_blocks.append(test_idx)

        for name, model in build_models().items():
            started = time.perf_counter()
            model.fit(features[train_idx], y[train_idx])
            fit_seconds = time.perf_counter() - started
            proba = model.predict_proba(features[test_idx])
            y_pred = CLASSES[proba.argmax(axis=1)]
            train_proba = model.predict_proba(features[train_idx])
            train_scores = score_fold(y[train_idx], CLASSES[train_proba.argmax(axis=1)], train_proba)
            fold_rows.append(
                {
                    **base, "model": name, **score_fold(y[test_idx], y_pred, proba),
                    **{f"train_{key}": value for key, value in train_scores.items()},
                    "fit_seconds": fit_seconds,
                }
            )
            if hasattr(model, "feature_importances_"):
                importance_rows.extend(
                    {"symbol": symbol, "fold": fold, "model": name, "feature": feature, "importance": value}
                    for feature, value in zip(feature_names, model.feature_importances_)
                )
            prediction_frames.append(
                pd.DataFrame(
                    {
                        "symbol": symbol, "model": name, "time": times[test_idx], "y_true": y[test_idx],
                        "y_pred": y_pred, "p_down": proba[:, 0], "p_flat": proba[:, 1], "p_up": proba[:, 2],
                        "r_next": r_next[test_idx],
                    }
                )
            )

        prior = np.bincount(y[train_idx], minlength=len(CLASSES)) / len(train_idx)
        draws = rng.choice(CLASSES, size=(RANDOM_BASELINE_RUNS, len(test_idx)), p=prior)
        random_draws.append(draws)
        scores = pd.DataFrame([score_fold(y[test_idx], draw, None) for draw in draws]).mean()
        fold_rows.append({**base, "model": "random", **scores.to_dict(), "fit_seconds": 0.0})

    test_all = np.concatenate(test_blocks)
    random_all = np.concatenate(random_draws, axis=1)
    backtests = {
        name: backtest(frame["y_pred"].to_numpy(), frame["r_next"].to_numpy())
        for name, frame in pd.concat(prediction_frames).groupby("model")
    }
    backtests["buy_and_hold"] = backtest(np.full(len(test_all), UP), r_next[test_all])
    random_results = pd.DataFrame([backtest(draw, r_next[test_all]) for draw in random_all])
    backtests["random"] = random_results.mean().to_dict()
    backtest_rows = [{"symbol": symbol, "model": name, **values} for name, values in backtests.items()]
    return (
        pd.DataFrame(fold_rows), pd.concat(prediction_frames),
        pd.DataFrame(backtest_rows), pd.DataFrame(importance_rows),
    )


def summarize(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    pooled = fold_metrics.assign(symbol="ALL")
    return (
        pd.concat([fold_metrics, pooled])
        .groupby(["symbol", "model"])[["accuracy", "f1_macro", "roc_auc", "fit_seconds"]]
        .agg(["mean", "std"])
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", default="1D")
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    parser.add_argument("--processed-root", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = [evaluate_symbol(s, args.resolution, args.processed_root) for s in args.symbols]
    fold_metrics = pd.concat([r[0] for r in results], ignore_index=True)
    predictions = pd.concat([r[1] for r in results], ignore_index=True)
    backtests = pd.concat([r[2] for r in results], ignore_index=True)
    importances = pd.concat([r[3] for r in results], ignore_index=True)

    output_dir = args.output_root / args.resolution
    output_dir.mkdir(parents=True, exist_ok=True)
    fold_metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    backtests.to_csv(output_dir / "backtest.csv", index=False)
    importances.to_csv(output_dir / "feature_importance.csv", index=False)
    summary = summarize(fold_metrics)
    summary.to_csv(output_dir / "summary.csv")

    pd.set_option("display.width", 200)
    print(summary.round(4).to_string())
    print(backtests.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
